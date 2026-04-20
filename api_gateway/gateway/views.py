import os
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import urlparse, parse_qs

import requests
from django.http import HttpRequest
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt


CUSTOMER_SERVICE_URL = os.environ.get('CUSTOMER_SERVICE_URL', 'http://customer-service:8001')
PRODUCT_SERVICE_URL = os.environ.get('PRODUCT_SERVICE_URL', 'http://product-service:8002')
CART_SERVICE_URL = os.environ.get('CART_SERVICE_URL', 'http://cart-service:8004')
STAFF_SERVICE_URL = os.environ.get('STAFF_SERVICE_URL', 'http://staff-service:8005')
AI_CHAT_SERVICE_URL = os.environ.get('AI_CHAT_SERVICE_URL', 'http://ai-chat-service:8006')
INTERACTION_SERVICE_URL = os.environ.get('INTERACTION_SERVICE_URL', 'http://interaction-service:8007')


def _format_vnd(amount) -> str:
	if amount is None:
		return ''
	try:
		d = Decimal(str(amount)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
	except (InvalidOperation, ValueError, TypeError):
		return ''
	value = int(d)
	return f"{value:,}".replace(',', '.') + ' VND'


def _normalize_product_for_template(item: dict) -> dict:
	# Normalizes product_service API shape into the existing templates' expected keys.
	brand = item.get('brand')
	images = item.get('images')
	image_url = item.get('thumbnail_url')
	if not image_url and isinstance(images, list) and images:
		image_url = images[0].get('url')
	if not image_url:
		image_url = item.get('image_url')

	price = item.get('base_price')
	if price is None:
		price = item.get('price')	
	price_display = _format_vnd(price)

	stock = item.get('stock')
	if stock is None:
		stock = 0

	attrs = item.get('attributes') or {}
	attribute_rows: list[dict[str, str]] = []

	def _clean_scalar(x) -> str:
		s = str(x).strip()
		if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
			s = s[1:-1].strip()
		return s

	def _add_row(label: str, value: str):
		label = (label or '').strip()
		value = (value or '').strip()
		if not label or not value:
			return
		attribute_rows.append({'label': label, 'value': value})

	if isinstance(attrs, dict):
		# Make arrays readable in UI, and flatten specs_raw into separate rows.
		specs_raw = None
		for specs_key in ('specs_raw', 'spec_raw', 'specs_raws', 'spec_raws'):
			if specs_key in attrs:
				specs_raw = attrs.get(specs_key)
				break

		for k, v in attrs.items():
			key = _clean_scalar(k)
			key = key.strip('"').strip("'")
			if not key:
				continue
			key_lc = key.lower()
			if key_lc in ('specs_raw', 'spec_raw', 'specs_raws', 'spec_raws'):
				continue
			if v is None:
				continue

			# purpose, screen_technologies are arrays in product data.
			if key_lc in ('purpose', 'screen_technologies') and isinstance(v, list):
				items = [_clean_scalar(it) for it in v if it is not None]
				items = [it for it in items if it]
				if not items:
					continue
				label = key.replace('_', ' ').strip().title()
				if key_lc == 'screen_technologies':
					val = "\n".join([f"• {it}" for it in items])
				else:
					val = ", ".join(items)
				_add_row(label, val)
				continue

			label = key.replace('_', ' ').strip().title()
			if isinstance(v, list):
				items = [_clean_scalar(it) for it in v if it is not None]
				items = [it for it in items if it]
				val = ", ".join(items) if items else ""
				_add_row(label, val)
			elif isinstance(v, dict):
				_add_row(label, json.dumps(v, ensure_ascii=False))
			else:
				_add_row(label, _clean_scalar(v))

		if isinstance(specs_raw, dict):
			for sk, sv in specs_raw.items():
				s_label = _clean_scalar(sk)
				if not s_label or sv is None:
					continue
				if isinstance(sv, list):
					items = [_clean_scalar(it) for it in sv if it is not None]
					items = [it for it in items if it]
					_add_row(s_label, "\n".join([f"• {it}" for it in items]))
				elif isinstance(sv, dict):
					_add_row(s_label, json.dumps(sv, ensure_ascii=False))
				else:
					_add_row(s_label, _clean_scalar(sv))

	return {
		'id': item.get('id'),
		'name': item.get('name'),
		'description': item.get('description', ''),
		'brand': brand.get('name') if isinstance(brand, dict) else brand,
		'price': price,
		'price_display': price_display,
		'stock': stock,
		'image_url': image_url,
		'currency': item.get('currency'),
		'attribute_rows': attribute_rows,
	}


def _session_customer_token(request: HttpRequest):
	return request.session.get('customer_token')


def _session_staff_token(request: HttpRequest):
	return request.session.get('staff_token')


def _headers_with_token(token: str | None):
	if not token:
		return {}
	return {'Authorization': f'Token {token}'}


def _ensure_session_id(request: HttpRequest) -> str:
	if not request.session.session_key:
		request.session.save()
	return request.session.session_key


def _get_customer_id(request: HttpRequest) -> str | None:
	token = _session_customer_token(request)
	if not token:
		return None
	cached = request.session.get('customer_id')
	if cached is not None:
		cid = str(cached).strip()
		return cid or None
	try:
		r = requests.get(
			CUSTOMER_SERVICE_URL.rstrip('/') + '/api/profile/',
			headers=_headers_with_token(token),
			timeout=10,
		)
		if r.status_code != 200:
			return None
		data = r.json() if r.content else {}
		cid = (data.get('id') or '')
		cid = str(cid).strip()
		if not cid:
			return None
		request.session['customer_id'] = cid
		return cid
	except requests.RequestException:
		return None


def _interaction_user_id(request: HttpRequest) -> str:
	cid = _get_customer_id(request)
	return cid if cid else 'guest_user'


def _log_interaction(
	request: HttpRequest,
	*,
	event_type: str,
	product_id: int | None = None,
	query_text: str | None = None,
	page: str | None = None,
	product_type: str | None = None,
	metadata: dict | None = None,
):
	url = INTERACTION_SERVICE_URL.rstrip('/') + '/api/events/'
	payload = {
		'user_id': _interaction_user_id(request),
		'session_id': _ensure_session_id(request),
		'event_type': event_type,
		'product_id': product_id,
		'query_text': query_text,
		'page': page,
		'product_type': product_type,
		'metadata': metadata or {},
	}
	try:
		requests.post(url, json=payload, timeout=2)
	except requests.RequestException:
		pass


def _extract_next_page(next_url: str | None):
	if not next_url:
		return None
	try:
		q = parse_qs(urlparse(next_url).query)
		page = q.get('page', [None])[0]
		return int(page) if page is not None else None
	except Exception:
		return None


def home(request):
	return render(request, 'home.html')


def product_list(request, product_type: str):
	if product_type == 'laptops':
		product_type_code = 'LAPTOP'
		title = 'Laptops'
	else:
		product_type_code = 'CLOTHES'
		title = 'Clothes'

	base = PRODUCT_SERVICE_URL.rstrip('/') + '/api/v1/products/'

	page = request.GET.get('page', 1)
	search = request.GET.get('search', '').strip()
	params = {'page': page, 'product_type': product_type_code}
	if search:
		params['q'] = search
		_log_interaction(
			request,
			event_type='search',
			query_text=search,
			page='products_list',
			product_type=product_type_code,
			metadata={'page': page},
		)

	error = None
	data = {}
	items = []
	try:
		r = requests.get(base, params=params, timeout=10)
		if r.status_code != 200:
			error = f'Upstream service error ({r.status_code}).'
		else:
			try:
				data = r.json() if r.content else {}
				items = data.get('results', data)
				if isinstance(items, list):
					items = [_normalize_product_for_template(p) for p in items]
			except Exception:
				error = 'Upstream service returned invalid JSON.'
	except requests.RequestException:
		error = 'Failed to reach upstream service.'
	ctx = {
		'title': title,
		'product_type': product_type,
		'items': items,
		'error': error,
		'search': search,
		'page': int(page) if str(page).isdigit() else 1,
		'next_page': _extract_next_page(data.get('next')) if isinstance(data, dict) else None,
		'prev_page': _extract_next_page(data.get('previous')) if isinstance(data, dict) else None,
	}
	return render(request, 'products/list.html', ctx)


def product_detail(request, product_type: str, product_id: int):
	url = PRODUCT_SERVICE_URL.rstrip('/') + f'/api/v1/products/{product_id}/'
	back = 'laptops' if product_type == 'laptops' else 'clothes'

	r = requests.get(url, timeout=10)
	if r.status_code != 200:
		return render(request, 'products/detail.html', {'item': None, 'product_type': product_type, 'back': back})

	product_type_code = 'LAPTOP' if product_type == 'laptops' else 'CLOTHES'
	_log_interaction(
		request,
		event_type='view',
		product_id=product_id,
		page='product_detail',
		product_type=product_type_code,
	)

	return render(
		request,
		'products/detail.html',
		{
			'item': _normalize_product_for_template(r.json()),
			'product_type': product_type,
			'back': back,
		},
	)


@require_http_methods(['GET', 'POST'])
def customer_register(request):
	if request.method == 'POST':
		payload = {
			'email': request.POST.get('email', '').strip(),
			'full_name': request.POST.get('full_name', '').strip(),
			'password': request.POST.get('password', ''),
		}
		r = requests.post(CUSTOMER_SERVICE_URL.rstrip('/') + '/api/register/', json=payload, timeout=10)
		if r.status_code in (200, 201):
			data = r.json()
			request.session['customer_token'] = data['token']
			return redirect('home')
		return render(request, 'customer/register.html', {'error': r.json().get('detail', 'Register failed')})

	return render(request, 'customer/register.html')


@require_http_methods(['GET', 'POST'])
def customer_login(request):
	if request.method == 'POST':
		payload = {
			'email': request.POST.get('email', '').strip(),
			'password': request.POST.get('password', ''),
		}
		r = requests.post(CUSTOMER_SERVICE_URL.rstrip('/') + '/api/login/', json=payload, timeout=10)
		if r.status_code == 200:
			data = r.json()
			request.session['customer_token'] = data['token']
			return redirect('home')
		return render(request, 'customer/login.html', {'error': 'Login failed'})
	return render(request, 'customer/login.html')


def customer_logout(request):
	request.session.pop('customer_token', None)
	return redirect('home')


def cart_view(request):
	token = _session_customer_token(request)
	if not token:
		return redirect('customer_login')

	r = requests.get(CART_SERVICE_URL.rstrip('/') + '/api/cart/', headers=_headers_with_token(token), timeout=10)
	cart = r.json() if r.status_code == 200 else None
	return render(request, 'cart/cart.html', {'cart': cart, 'error': None if cart else 'Failed to load cart'})


@require_http_methods(['POST'])
def cart_add(request):
	token = _session_customer_token(request)
	if not token:
		return redirect('customer_login')

	payload = {
		'product_type': request.POST.get('product_type'),
		'product_id': int(request.POST.get('product_id')),
		'quantity': int(request.POST.get('quantity', '1')),
	}
	requests.post(
		CART_SERVICE_URL.rstrip('/') + '/api/cart/items/',
		json=payload,
		headers=_headers_with_token(token),
		timeout=10,
	)

	pt = payload.get('product_type')
	pt_code = 'LAPTOP' if pt == 'laptop' else 'CLOTHES' if pt == 'clothes' else None
	_log_interaction(
		request,
		event_type='add_to_cart',
		product_id=payload.get('product_id'),
		page='cart',
		product_type=pt_code,
	)

	return redirect('cart')


@require_http_methods(['POST'])
def cart_item_update(request, item_id: int):
	token = _session_customer_token(request)
	if not token:
		return redirect('customer_login')
	payload = {'quantity': int(request.POST.get('quantity', '1'))}
	requests.patch(
		CART_SERVICE_URL.rstrip('/') + f'/api/cart/items/{item_id}/',
		json=payload,
		headers=_headers_with_token(token),
		timeout=10,
	)
	return redirect('cart')


@require_http_methods(['POST'])
def cart_item_delete(request, item_id: int):
	token = _session_customer_token(request)
	if not token:
		return redirect('customer_login')
	requests.delete(
		CART_SERVICE_URL.rstrip('/') + f'/api/cart/items/{item_id}/',
		headers=_headers_with_token(token),
		timeout=10,
	)
	return redirect('cart')


@require_http_methods(['POST'])
def checkout(request):
	token = _session_customer_token(request)
	if not token:
		return redirect('customer_login')
	r = requests.post(
		CART_SERVICE_URL.rstrip('/') + '/api/checkout/',
		headers=_headers_with_token(token),
		timeout=10,
	)
	if r.status_code not in (200, 201):
		return redirect('cart')

	order = r.json() if r.content else {}
	items = order.get('items') if isinstance(order, dict) else []
	if isinstance(items, list):
		for it in items:
			pt = it.get('product_type')
			pt_code = 'LAPTOP' if pt == 'laptop' else 'CLOTHES' if pt == 'clothes' else None
			pid = it.get('product_id')
			if pid and pt_code:
				_log_interaction(
					request,
					event_type='purchase',
					product_id=int(pid),
					page='checkout_success',
					product_type=pt_code,
					metadata={'order_id': order.get('id')},
				)

	return render(request, 'cart/checkout_success.html', {'order': order})


@require_http_methods(['GET', 'POST'])
def staff_login(request):
	if request.method == 'POST':
		payload = {
			'username': request.POST.get('username', '').strip(),
			'password': request.POST.get('password', ''),
		}
		r = requests.post(STAFF_SERVICE_URL.rstrip('/') + '/api/login/', json=payload, timeout=10)
		if r.status_code == 200:
			request.session['staff_token'] = r.json()['token']
			return redirect('staff_dashboard')
		return render(request, 'staff/login.html', {'error': 'Login failed'})
	return render(request, 'staff/login.html')


def staff_logout(request):
	request.session.pop('staff_token', None)
	return redirect('home')


def staff_dashboard(request):
	token = _session_staff_token(request)
	if not token:
		return redirect('staff_login')

	active_tab = request.GET.get('tab', 'products')
	if active_tab not in ('products', 'orders'):
		active_tab = 'products'

	orders = []
	r = requests.get(
		STAFF_SERVICE_URL.rstrip('/') + '/api/proxy/orders/api/orders/',
		headers=_headers_with_token(token),
		timeout=10,
	)
	if r.status_code == 200:
		orders = r.json()

	laptops = []
	lr = requests.get(
		STAFF_SERVICE_URL.rstrip('/') + '/api/proxy/products/api/v1/products/',
		params={'product_type': 'LAPTOP'},
		headers=_headers_with_token(token),
		timeout=10,
	)
	if lr.status_code == 200:
		data = lr.json()
		laptops = data.get('results', data)

	clothes = []
	sr = requests.get(
		STAFF_SERVICE_URL.rstrip('/') + '/api/proxy/products/api/v1/products/',
		params={'product_type': 'CLOTHES'},
		headers=_headers_with_token(token),
		timeout=10,
	)
	if sr.status_code == 200:
		data = sr.json()
		clothes = data.get('results', data)

	return render(
		request,
		'staff/dashboard.html',
		{
			'orders': orders,
			'laptops': laptops,
			'clothes': clothes,
			'active_tab': active_tab,
		},
	)


@require_http_methods(['POST'])
def staff_product_create(request, product_type: str):
	token = _session_staff_token(request)
	if not token:
		return redirect('staff_login')
	if product_type == 'laptops':
		product_type_code = 'LAPTOP'
		category_slug = 'laptops'
	else:
		product_type_code = 'CLOTHES'
		category_slug = 'clothes'

	payload = {
		'product_type_code': product_type_code,
		'brand_name': request.POST.get('brand', '').strip(),
		'category_slug': category_slug,
		'name': request.POST.get('name', '').strip(),
		'description': request.POST.get('description', '').strip(),
		'base_price': request.POST.get('price', '0'),
		'currency': 'VND',
		'stock': int(request.POST.get('stock', '0')),
		'image_urls': [request.POST.get('image_url', '').strip()],
		'attributes': {},
		'is_active': True,
	}
	url = STAFF_SERVICE_URL.rstrip('/') + '/api/proxy/products/api/v1/products/'
	requests.post(url, json=payload, headers=_headers_with_token(token), timeout=10)
	return redirect('staff_dashboard')


@require_http_methods(['GET', 'POST'])
def staff_product_edit(request, product_type: str, product_id: int):
	token = _session_staff_token(request)
	if not token:
		return redirect('staff_login')

	base = STAFF_SERVICE_URL.rstrip('/') + '/api/proxy/products'
	detail_path = f'api/v1/products/{product_id}/'

	if request.method == 'POST':
		if product_type == 'laptops':
			product_type_code = 'LAPTOP'
			category_slug = 'laptops'
		else:
			product_type_code = 'CLOTHES'
			category_slug = 'clothes'
		payload = {
			'product_type_code': product_type_code,
			'brand_name': request.POST.get('brand', '').strip(),
			'category_slug': category_slug,
			'name': request.POST.get('name', '').strip(),
			'description': request.POST.get('description', '').strip(),
			'base_price': request.POST.get('price', '0'),
			'currency': 'VND',
			'stock': int(request.POST.get('stock', '0')),
			'image_urls': [request.POST.get('image_url', '').strip()],
			'attributes': {},
			'is_active': True,
		}
		requests.put(
			f'{base}/{detail_path}',
			json=payload,
			headers=_headers_with_token(token),
			timeout=10,
		)
		return redirect('staff_dashboard')

	r = requests.get(f'{base}/{detail_path}', headers=_headers_with_token(token), timeout=10)
	item = _normalize_product_for_template(r.json()) if r.status_code == 200 else None
	return render(request, 'staff/edit_product.html', {'item': item, 'product_type': product_type})


@require_http_methods(['POST'])
def staff_product_delete(request, product_type: str, product_id: int):
	token = _session_staff_token(request)
	if not token:
		return redirect('staff_login')

	url = STAFF_SERVICE_URL.rstrip('/') + f'/api/proxy/products/api/v1/products/{product_id}/'
	requests.delete(url, headers=_headers_with_token(token), timeout=10)
	return redirect('staff_dashboard')


@csrf_exempt
@require_http_methods(['POST'])
def chat_message_proxy(request):
	try:
		payload = json.loads(request.body.decode('utf-8') or '{}')
	except (json.JSONDecodeError, UnicodeDecodeError):
		return JsonResponse({'detail': 'Invalid JSON payload'}, status=400)

	if not str(payload.get('user_id') or '').strip():
		payload['user_id'] = _interaction_user_id(request)

	msg = (payload.get('message') or '').strip()
	if msg:
		ctx = payload.get('context') if isinstance(payload.get('context'), dict) else {}
		_log_interaction(
			request,
			event_type='chat',
			query_text=msg,
			page='chat_widget',
			product_type=ctx.get('product_type'),
			metadata={'page': ctx.get('page')},
		)

	try:
		r = requests.post(
			AI_CHAT_SERVICE_URL.rstrip('/') + '/api/v1/chat/message/',
			json=payload,
			timeout=25,
		)
		data = r.json() if r.content else {'detail': 'Empty response from ai_chat_service'}
		return JsonResponse(data, status=r.status_code)
	except requests.RequestException:
		return JsonResponse(
			{'detail': 'Unable to reach ai_chat_service'},
			status=503,
		)
