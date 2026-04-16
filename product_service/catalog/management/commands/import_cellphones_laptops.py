import json
import re
from decimal import Decimal
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Brand, Category, Product, ProductImage, ProductType


DEFAULT_HEADERS = {
	'User-Agent': (
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
		'AppleWebKit/537.36 (KHTML, like Gecko) '
		'Chrome/124.0.0.0 Safari/537.36'
	),
	'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
	'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
	'Connection': 'keep-alive',
}


SPEC_KEY_MAP = {
	# Keys aligned to `entity_and_db_design.md` Laptop example/schema where possible.
	'CPU': 'processor',
	'Vi xử lý': 'processor',
	'Loại card đồ họa': 'gpu_model',
	'Dung lượng RAM': 'ram',
	'Ổ cứng': 'storage',
	'Kích thước màn hình': 'screen_size_inch',
	'Độ phân giải': 'screen_resolution',
	'Công nghệ màn hình': 'screen_technologies',
	'Hệ điều hành': 'os',
	'Pin': 'battery',
	'Trọng lượng': 'weight_kg',
	'Kích thước': 'size_cm',
	'Cổng kết nối': 'ports',
	'Kết nối không dây': 'connectivity',
	'Webcam': 'webcam',

	# Keep some extra (schema allows additionalProperties).
	'Chip AI': 'ai_chip',
	'Loại RAM': 'ram_type',
	'Số khe ram': 'ram_slots',
	'Màn hình chống chói': 'screen_anti_glare',
	'Độ phủ màu': 'screen_color_gamut',
	'Tần số quét': 'screen_refresh_rate',
	'Bàn phím': 'keyboard',
}


CONTACT_FOR_PRICE_PHRASE = 'Liên hệ để báo giá'


USED_SUFFIX_KEYWORDS = [
	'cũ đẹp',
	'cũ trầy xước',
	'cũ trầy',
	'cũ xước cấn',
	'cũ xước',
	'xước cấn',
	'trầy xước',
]


def _extract_technical_specs(html: str) -> dict[str, str]:
	soup = BeautifulSoup(html, 'lxml')
	block = soup.find(id='thong-so-ky-thuat')
	if not block:
		return {}

	specs: dict[str, str] = {}
	for tr in block.find_all('tr'):
		cells = tr.find_all(['th', 'td'])
		if len(cells) < 2:
			continue
		k = cells[0].get_text(' ', strip=True)
		v = cells[1].get_text(' ', strip=True)
		if k and v:
			specs[k] = v
	return specs


def _should_skip_contact_for_price(html: str) -> bool:
	soup = BeautifulSoup(html, 'lxml')
	price_box = soup.find('div', class_='box-product-price')
	if not price_box:
		return False
	text = price_box.get_text(' ', strip=True)
	return CONTACT_FOR_PRICE_PHRASE.lower() in text.lower()


def _extract_seo_description(html: str) -> str | None:
	"""Return SEO description from cpsContentSEO: h2 + first 3 <p>.

	If cpsContentSEO missing (or not enough content), return None.
	"""
	soup = BeautifulSoup(html, 'lxml')
	# CellphoneS commonly uses id="cpsContentSEO" for the SEO html block.
	root = soup.find(id='cpsContentSEO')
	if not root:
		root = soup.find(class_='cpsContentSEO')
	if not root:
		return None
	h2 = root.find('h2')
	paras = root.find_all('p')
	if not h2 or len(paras) < 3:
		return None
	title = h2.get_text(' ', strip=True)
	chunks = [p.get_text(' ', strip=True) for p in paras[:3]]
	chunks = [c for c in chunks if c]
	if not title or len(chunks) < 3:
		return None
	return '\n\n'.join([title, *chunks])


def _clean_laptop_name(name: str) -> str:
	"""Keep base product name; drop used-condition suffix often after '-' (e.g. '... - Cũ đẹp')."""
	base = name.strip()
	if not base:
		return base

	# Prefer splitting on ' - ' to avoid breaking model names that contain '-' without spaces.
	if ' - ' in base:
		left, right = base.split(' - ', 1)
		r = right.strip().lower()
		if any(k in r for k in USED_SUFFIX_KEYWORDS):
			return left.strip()
		return base

	# Fallback: if last segment after '-' looks like a used-condition phrase.
	if '-' in base:
		left, right = base.rsplit('-', 1)
		r = right.strip().lower()
		if any(k in r for k in USED_SUFFIX_KEYWORDS):
			return left.strip()
	return base


def _parse_weight_kg(value: str) -> float | None:
	# Common formats: "1.24 kg", "1,24 kg", "1240 g"
	v = (value or '').strip().lower()
	v = v.replace(',', '.')
	m = re.search(r"(\d+(?:\.\d+)?)\s*kg\b", v)
	if m:
		try:
			return float(m.group(1))
		except Exception:
			return None
	m = re.search(r"(\d+(?:\.\d+)?)\s*g\b", v)
	if m:
		try:
			return float(m.group(1)) / 1000.0
		except Exception:
			return None
	return None


def _parse_size_cm(value: str) -> dict | None:
	"""Parse size string into {length,width,height} in cm when possible."""
	v = (value or '').strip().lower()
	if not v:
		return None
	# Normalize separators
	v = v.replace(',', '.')
	# Capture 3 numbers like 304.1 x 215 x 11.3 mm
	m = re.search(
		r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)(?:\s*(mm|cm))?",
		v,
	)
	if not m:
		return None
	unit = (m.group(4) or 'mm').strip().lower()
	try:
		length = float(m.group(1))
		width = float(m.group(2))
		height = float(m.group(3))
	except Exception:
		return None
	if unit == 'mm':
		length /= 10.0
		width /= 10.0
		height /= 10.0
	return {'length': length, 'width': width, 'height': height}


def _split_listish(value: str) -> list[str]:
	"""Split common comma/semicolon/newline separated lists into strings."""
	if not value:
		return []
	# Replace bullets and pipes
	v = value.replace('•', '\n').replace('|', ',')
	parts = re.split(r"[\n;,]+", v)
	items = [p.strip() for p in parts if p and p.strip()]
	# Deduplicate while preserving order
	seen: set[str] = set()
	result: list[str] = []
	for it in items:
		key = it.lower()
		if key in seen:
			continue
		seen.add(key)
		result.append(it)
	return result


def _map_specs_to_attributes(specs: dict[str, str]) -> tuple[dict, dict[str, str]]:
	attributes: dict = {}
	unmapped: dict[str, str] = {}
	for k, v in specs.items():
		mapped = SPEC_KEY_MAP.get(k)
		if mapped:
			attributes[mapped] = v
		else:
			unmapped[k] = v

	# Normalize types/structures to align with design.
	if 'screen_size_inch' in attributes:
		m = re.search(r"(\d+(?:\.\d+)?)", str(attributes['screen_size_inch']))
		if m:
			try:
				attributes['screen_size_inch'] = float(m.group(1))
			except Exception:
				pass

	if 'screen_technologies' in attributes and isinstance(attributes['screen_technologies'], str):
		attributes['screen_technologies'] = _split_listish(attributes['screen_technologies'])

	if 'ports' in attributes and isinstance(attributes['ports'], str):
		attributes['ports'] = _split_listish(attributes['ports'])

	if 'connectivity' in attributes and isinstance(attributes['connectivity'], str):
		attributes['connectivity'] = _split_listish(attributes['connectivity'])

	if 'weight_kg' in attributes:
		w = _parse_weight_kg(str(attributes['weight_kg']))
		if w is not None:
			attributes['weight_kg'] = w

	if 'size_cm' in attributes:
		size = _parse_size_cm(str(attributes['size_cm']))
		if size is not None:
			attributes['size_cm'] = size

	return attributes, unmapped


def _extract_json_ld_objects(html: str):
	soup = BeautifulSoup(html, 'lxml')	
	objects = []
	for tag in soup.find_all('script', attrs={'type': 'application/ld+json'}):
		text = (tag.string or tag.get_text() or '').strip()
		if not text:
			continue
		try:
			data = json.loads(text)
		except Exception:
			continue

		if isinstance(data, list):
			objects.extend([o for o in data if isinstance(o, dict)])
		elif isinstance(data, dict):
			objects.append(data)
	return objects


def _pick_product_ld(objects: list[dict]) -> dict | None:
	# Prefer a Product object, but some pages embed in @graph.
	candidates: list[dict] = []
	for obj in objects:
		if obj.get('@type') == 'Product':
			candidates.append(obj)
		graph = obj.get('@graph')
		if isinstance(graph, list):
			for g in graph:
				if isinstance(g, dict) and g.get('@type') == 'Product':
					candidates.append(g)
	return candidates[0] if candidates else None


def _parse_price(product_ld: dict) -> Decimal | None:
	offers = product_ld.get('offers')
	if isinstance(offers, dict):
		price = offers.get('price')
		if price is None:
			return None
		try:
			return Decimal(str(price))
		except Exception:
			return None
	if isinstance(offers, list) and offers:
		for offer in offers:
			if isinstance(offer, dict) and offer.get('price') is not None:
				try:
					return Decimal(str(offer.get('price')))
				except Exception:
					continue
	return None


def _parse_brand_name(product_ld: dict) -> str | None:
	brand = product_ld.get('brand')
	if isinstance(brand, dict):
		name = brand.get('name')
		return str(name).strip() if name else None
	if isinstance(brand, str):
		return brand.strip() or None
	return None


def _parse_images(product_ld: dict) -> list[str]:
	images = product_ld.get('image')
	if isinstance(images, str):
		return [images]
	if isinstance(images, list):
		return [str(u) for u in images if u]
	return []


def _normalize_money(amount: Decimal | None) -> Decimal:
	return amount if amount is not None else Decimal('0')


def _guess_laptop_attributes_from_name(name: str) -> dict:
	"""Deprecated: keep for backward compatibility, but return empty to avoid
	adding non-design keys like ram_gb/storage_gb.
	"""
	return {}


class Command(BaseCommand):
	help = 'Import laptop products from CellphoneS product pages (JSON-LD based).'

	def add_arguments(self, parser):
		parser.add_argument('--urls', nargs='+', help='One or more CellphoneS product URLs to import')
		parser.add_argument('--sitemap', help='Sitemap URL containing product URLs (optional)')
		parser.add_argument('--limit', type=int, default=20, help='Max URLs to import from sitemap')
		parser.add_argument('--dry-run', action='store_true', help='Fetch/parse but do not write to DB')

	def handle(self, *args, **options):
		urls: list[str] = options.get('urls') or []
		sitemap_url: str | None = options.get('sitemap')
		limit: int = options.get('limit')
		dry_run: bool = options.get('dry_run')

		if not urls and not sitemap_url:
			raise SystemExit('Provide --urls ... or --sitemap ...')

		if sitemap_url:
			urls = self._load_urls_from_sitemap(sitemap_url, limit=limit)

		if dry_run:
			laptop_type = ProductType(code='LAPTOP', name='Laptop', attribute_schema={})
			default_category = Category(slug='laptops', name='Laptops')
		else:
			laptop_type, _ = ProductType.objects.get_or_create(
				code='LAPTOP',
				defaults={'name': 'Laptop', 'attribute_schema': {}},
			)

			default_category, _ = Category.objects.get_or_create(
				slug='laptops',
				defaults={'name': 'Laptops', 'parent': None},
			)

		self.stdout.write(f'Importing {len(urls)} URL(s)...')
		created = 0
		updated = 0
		skipped = 0
		failed = 0

		for url in urls:
			try:
				result = self._import_one(
					url=url,
					product_type=laptop_type,
					category=default_category,
					dry_run=dry_run,
				)
			except Exception as exc:
				failed += 1
				self.stderr.write(f'FAILED {url}: {exc}')
				continue

			if result == 'created':
				created += 1
			elif result == 'updated':
				updated += 1
			elif result == 'skipped':
				skipped += 1

		self.stdout.write(self.style.SUCCESS(
			f'Done. created={created} updated={updated} skipped={skipped} failed={failed}'
		))

	def _load_urls_from_sitemap(self, sitemap_url: str, limit: int) -> list[str]:
		r = requests.get(sitemap_url, headers=DEFAULT_HEADERS, timeout=30)
		r.raise_for_status()
		text = r.text

		# Very small XML parser via regex to avoid extra deps.
		locs = re.findall(r"<loc>(.*?)</loc>", text)
		# Only import real laptop product pages (avoid accessories like "balo-laptop").
		filtered: list[str] = []
		for u in locs:
			if not u.startswith('https://cellphones.com.vn/'):
				continue
			if re.match(r"^https://cellphones\.com\.vn/(laptop|macbook)-[a-z0-9\-]+\.html$", u):
				filtered.append(u)
		return filtered[:limit]

	def _import_one(self, url: str, product_type: ProductType, category: Category, dry_run: bool) -> str:
		r = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
		r.raise_for_status()
		html = r.text

		# Skip products that require contact for price.
		if _should_skip_contact_for_price(html):
			self.stdout.write(f'[SKIP] contact-for-price: {url}')
			return 'skipped'

		# Description requirement: h2 + 3 <p> inside cpsContentSEO; if missing, skip product.
		seo_description = _extract_seo_description(html)
		if not seo_description:
			self.stdout.write(f'[SKIP] missing cpsContentSEO: {url}')
			return 'skipped'

		objects = _extract_json_ld_objects(html)
		product_ld = _pick_product_ld(objects)
		if not product_ld:
			raise ValueError('No JSON-LD Product found')

		name = (product_ld.get('name') or '').strip()
		if not name:
			raise ValueError('Missing product name in JSON-LD')
		name = _clean_laptop_name(name)

		brand_name = _parse_brand_name(product_ld) or 'Unknown'
		brand, _ = Brand.objects.get_or_create(name=brand_name)

		price = _normalize_money(_parse_price(product_ld))
		currency = 'VND'
		if isinstance(product_ld.get('offers'), dict) and product_ld['offers'].get('priceCurrency'):
			currency = str(product_ld['offers']['priceCurrency'])

		images = _parse_images(product_ld)
		if images:
			images = [urljoin(url, u) for u in images]

		attributes = _guess_laptop_attributes_from_name(name)
		specs = _extract_technical_specs(html)
		mapped_specs, unmapped_specs = _map_specs_to_attributes(specs)
		attributes.update(mapped_specs)
		if unmapped_specs:
			attributes['specs_raw'] = unmapped_specs
		attributes['source'] = 'cellphones'

		description = seo_description
		if dry_run:
			self.stdout.write(
				f'[DRY] {name} | {brand_name} | {price} {currency} | images={len(images)} | desc=seo'
			)
			return 'created'

		with transaction.atomic():
			product, created = Product.objects.update_or_create(
				source_url=url,
				defaults={
					'product_type': product_type,
					'brand': brand,
					'category': category,
					'name': name,
					'description': description,
					'base_price': price,
					'currency': currency,
					'attributes': attributes,
					'is_active': True,
				},
			)

			if images:
				# replace existing images for idempotency
				ProductImage.objects.filter(product=product).delete()
				ProductImage.objects.bulk_create([
					ProductImage(product=product, url=u, sort_order=i)
					for i, u in enumerate(images)
				])

		return 'created' if created else 'updated'

	# Slug not stored in current Product model.
