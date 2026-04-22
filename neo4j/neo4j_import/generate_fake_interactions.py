import argparse
import csv
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


@dataclass(frozen=True)
class UserProfile:
    user_id: str
    preferred_brand: str
    preferred_budget: str
    preferred_purpose: str
    device: str
    referrer: str
    chat_prone: bool
    impatient: bool


@dataclass(frozen=True)
class Behavior:
    event_type: str
    page: str
    needs_product: bool = False
    needs_text: bool = False
    duration_ms_range: tuple[int, int] | None = None


BEHAVIORS: list[Behavior] = [
    Behavior("search", page="products_list", needs_text=True),
    Behavior("view", page="product_detail", needs_product=True, duration_ms_range=(18000, 75000)),
    Behavior("filter", page="products_list", needs_text=True),
    Behavior("sort", page="products_list", needs_text=True),
    Behavior("add_to_wishlist", page="wishlist", needs_product=True, duration_ms_range=(600, 2500)),
    Behavior("add_to_cart", page="cart", needs_product=True, duration_ms_range=(1500, 9000)),
    Behavior("remove_from_cart", page="cart", needs_product=True, duration_ms_range=(800, 6000)),
    Behavior("checkout_start", page="checkout", duration_ms_range=(2000, 12000)),
    Behavior("purchase", page="checkout_success", needs_product=True, duration_ms_range=(4000, 15000)),
    Behavior("chat", page="chat_widget", needs_text=True),
]

BRANDS = ["ASUS", "Lenovo", "Acer", "Dell", "HP", "MSI"]
PURPOSES = ["văn phòng", "mỏng nhẹ", "gaming", "đồ hoạ - kỹ thuật", "laptop AI"]
DEVICES = ["desktop", "mobile"]
REFERRERS = ["direct", "organic", "ads", "referral"]
CPU_KEYWORDS = [
    "core i5",
    "core i7",
    "ultra 5",
    "ultra 7",
    "ryzen 5",
    "ryzen 7",
    "ryzen ai",
]
GPU_KEYWORDS = ["rtx 2050", "rtx", "intel arc", "radeon", "iris xe"]
BUDGETS = [
    "dưới 10tr",
    "10-15tr",
    "15-20tr",
    "tầm 20tr",
    "20-25tr",
    "25-30tr",
    "dưới 30tr",
]

BASE_SEARCH_QUERIES = [
    # purpose + budget
    "laptop đồ hoạ kỹ thuật tầm 20 triệu",
    "laptop đồ hoạ kỹ thuật 20-30tr",
    "laptop mỏng nhẹ pin trâu",
    "laptop mỏng nhẹ dưới 20tr",
    "laptop văn phòng dưới 15tr",
    "laptop 14 inch nhẹ dưới 1.5kg",
    "laptop học IT + lập trình",
    "laptop pin tốt cho sinh viên",
    "laptop màn hình đẹp OLED",
    "laptop màn hình 16 inch 16:10",
    "laptop AI copilot",
    "laptop ryzen ai 7",
    "laptop core ultra 5",
    "laptop core ultra 7",
    "laptop gaming rtx",
    "laptop rtx 2050 4gb",
    "laptop tản nhiệt tốt chơi game",
    "laptop gọn nhẹ mang đi làm",
    "laptop 32gb ram",
    "laptop ram 16gb ssd 512",
    "laptop ssd 1tb",
    "laptop thiết kế đồ hoạ kiến trúc",
    "laptop render nhẹ sketchup",
    "laptop excel kế toán văn phòng",
    "laptop họp online webcam fhd",
    "laptop có sạc type-c",
    "laptop có thunderbolt 4",
    "laptop mới nhất 2026",
]

FILTER_TEXTS = [
    # purpose
    "filter: purpose=mỏng nhẹ",
    "filter: purpose=văn phòng",
    "filter: purpose=laptop AI",
    "filter: purpose=gaming",
    "filter: purpose=đồ hoạ - kỹ thuật",
    # price
    "filter: price<=10000000",
    "filter: price<=15000000",
    "filter: price<=20000000",
    "filter: price<=25000000",
    "filter: price<=30000000",
    "filter: price>=20000000",
    # screen
    "filter: screen_size=14",
    "filter: screen_size=15.6",
    "filter: screen_size=16",
    "filter: screen=oled",
    "filter: screen=120hz",
    "filter: ratio=16:10",
    # memory/storage
    "filter: ram>=8",
    "filter: ram>=16",
    "filter: ram>=32",
    "filter: storage>=512",
    "filter: storage>=1024",
    # portability
    "filter: weight<=1.5",
    "filter: battery>=57wh",
    # brands
    "filter: brand=asus",
    "filter: brand=lenovo",
    "filter: brand=acer",
    "filter: brand=dell",
    "filter: brand=hp",
    "filter: brand=msi",
    # ports
    "filter: port=usb-c",
    "filter: port=thunderbolt",
]

SORT_TEXTS = [
    "sort: price_asc",
    "sort: price_desc",
    "sort: newest",
]

CHAT_TEXTS = [
    "Máy này có phù hợp học IT + làm đồ hoạ không?",
    "Pin dùng văn phòng được bao lâu?",
    "Máy có nóng khi chạy lâu không?",
    "Màn hình có đẹp để làm thiết kế không?",
    "Con máy này có nâng cấp RAM/SSD được không?",
    "Máy có hỗ trợ sạc Type-C không?",
    "Webcam có nét để học/meeting online không?",
    "Bàn phím gõ có sướng không, có đèn không?",
    "Loa nghe nhạc ổn không?",
    "Màn hình OLED có bị bóng/nhức mắt không?",
    "Máy này chạy AutoCAD/Revit nhẹ ổn không?",
    "Có phù hợp làm Photoshop/Illustrator không?",
    "Card đồ hoạ này chơi game mức nào?",
    "Máy có nâng cấp thêm SSD được không?",
    "Máy có khe RAM nâng cấp không hay hàn chết?",
    "Trọng lượng khoảng bao nhiêu kg?",
    "Bảo hành bao lâu, có đổi trả không?",
    "Tản nhiệt khi render có ổn không?",
    "Máy có cổng HDMI/USB-A đầy đủ không?",
    "Có hỗ trợ Thunderbolt/USB4 không?",
    "Máy có bị ồn quạt khi làm việc nặng không?",
    "Có phù hợp mang đi học hằng ngày không?",
    "Màn hình 14 inch làm việc có đủ không?",
    "Máy này có Copilot/AI NPU không?",
    "SSD 512GB có đủ dùng không hay nên 1TB?",
]


def _product_brand(product_id: int) -> str:
    # Deterministic pseudo-metadata to enable personalization without needing a full product catalog.
    return BRANDS[product_id % len(BRANDS)]


def _product_budget(product_id: int) -> str:
    return BUDGETS[product_id % len(BUDGETS)]


def _weighted_choice(items: list[str], weights: list[float]) -> str:
    # random.choices exists, but keep explicit for clarity + typing.
    return random.choices(items, weights=weights, k=1)[0]


def _make_user_profile(user_idx: int) -> UserProfile:
    user_id = f"US_{user_idx:03d}"
    preferred_brand = random.choice(BRANDS)
    preferred_budget = random.choice(BUDGETS)
    preferred_purpose = random.choice(PURPOSES)
    device = _weighted_choice(DEVICES, [0.65, 0.35])
    referrer = _weighted_choice(REFERRERS, [0.35, 0.40, 0.20, 0.05])

    # Personal traits influence behavior.
    chat_prone = random.random() < 0.35
    impatient = random.random() < 0.25

    return UserProfile(
        user_id=user_id,
        preferred_brand=preferred_brand,
        preferred_budget=preferred_budget,
        preferred_purpose=preferred_purpose,
        device=device,
        referrer=referrer,
        chat_prone=chat_prone,
        impatient=impatient,
    )


def _pick_product_for_user(profile: UserProfile, product_ids: list[int]) -> int:
    # Bias towards products whose pseudo brand matches user preference.
    preferred = [pid for pid in product_ids if _product_brand(pid) == profile.preferred_brand]
    if preferred and random.random() < 0.75:
        return random.choice(preferred)
    return random.choice(product_ids)


def _build_search_query(profile: UserProfile, search_queries: list[str]) -> str:
    # Mix base queries with user preference tokens.
    if random.random() < 0.6:
        return random.choice(search_queries)
    brand = profile.preferred_brand.lower()
    # Put purpose + budget + brand to reinforce a learnable pattern.
    return f"laptop {profile.preferred_purpose} {brand} {profile.preferred_budget}".strip()


def _filter_text_for_user(profile: UserProfile) -> str:
    # Encourage consistent filters for the same user.
    if random.random() < 0.45:
        return f"filter: purpose={profile.preferred_purpose}"
    if random.random() < 0.45:
        return f"filter: brand={profile.preferred_brand.lower()}"
    return random.choice(FILTER_TEXTS)


def _duration_ms(behavior: Behavior, profile: UserProfile) -> str:
    if not behavior.duration_ms_range:
        return ""
    low, high = behavior.duration_ms_range
    if profile.impatient:
        high = max(low, int(high * 0.7))
    return str(random.randint(low, high))


def _advance_time(current_dt: datetime, profile: UserProfile) -> tuple[datetime, int]:
    # Faster users have smaller gaps.
    if profile.impatient:
        gap_s = random.randint(5, 90)
    else:
        gap_s = random.randint(10, 240)
    return current_dt + timedelta(seconds=gap_s), gap_s


def _generate_session_events(
    *,
    profile: UserProfile,
    session_id: str,
    start_dt: datetime,
    product_ids: list[int],
    search_queries: list[str],
    max_events: int,
    difficulty: str,
) -> list[dict[str, str]]:
    """Generate a single session with constraints (state machine).

    Constraints enforced:
    - checkout_start only if cart_size > 0
    - purchase only if checkout_started and cart_size > 0
    - remove_from_cart only if cart_size > 0
    - add_to_cart usually after view
    """

    events: list[dict[str, str]] = []
    current_dt = start_dt
    cart: list[int] = []
    last_viewed: int | None = None
    checkout_started = False

    # Track required actions for easy mode so we always generate
    # at least the minimum label set when max_events allows.
    did_filter = False
    did_remove = False

    # Session goal influences transitions.
    #  - buy: likely ends with purchase
    #  - browse: explores but no checkout
    #  - abandon: adds to cart then removes/leaves
    #  - support: more chat
    if difficulty == "easy":
        # In easy mode we still want predictability, but the distribution should be more realistic:
        # - browsing events (search/view/filter/wishlist) dominate
        # - cart/checkout/purchase happen less often
        goal = _weighted_choice(["buy", "browse"], [0.20, 0.80])
    else:
        goal = _weighted_choice(
            ["buy", "browse", "abandon", "support"],
            [0.35, 0.35, 0.20, 0.10],
        )

    # Step 1-3: entry funnel
    entry_steps = 1 if difficulty == "easy" else random.randint(1, 3)
    for _ in range(entry_steps):
        et = "search" if difficulty == "easy" else _weighted_choice(["search", "filter", "sort"], [0.55, 0.30, 0.15])
        if et == "search":
            query_text = _build_search_query(profile, search_queries)
            events.append(
                {
                    "event_type": "search",
                    "page": "products_list",
                    "product_id": "",
                    "query_text": query_text,
                    "duration_ms": "",
                    "product_type": "LAPTOP",
                }
            )
            # In easy mode, deterministically add a filter step right after search
            # (at most once per session) to guarantee the dataset contains 'filter'.
            if difficulty == "easy" and not did_filter and (max_events - len(events)) >= 2:
                events.append(
                    {
                        "event_type": "filter",
                        "page": "products_list",
                        "product_id": "",
                        "query_text": _filter_text_for_user(profile),
                        "duration_ms": "",
                        "product_type": "LAPTOP",
                    }
                )
                did_filter = True
        elif et == "filter":
            events.append(
                {
                    "event_type": "filter",
                    "page": "products_list",
                    "product_id": "",
                    "query_text": _filter_text_for_user(profile),
                    "duration_ms": "",
                    "product_type": "LAPTOP",
                }
            )
            did_filter = True
        else:
            events.append(
                {
                    "event_type": "sort",
                    "page": "products_list",
                    "product_id": "",
                    "query_text": random.choice(SORT_TEXTS),
                    "duration_ms": "",
                    "product_type": "LAPTOP",
                }
            )

    # Main loop
    while len(events) < max_events:
        remaining = max_events - len(events)

        # In easy mode, make next-action much more predictable.
        # This is intentionally simplified to make accuracy > 0.6 achievable.
        if difficulty == "easy" and events:
            last_ev = events[-1]["event_type"]
            if last_ev in {"search", "filter", "sort"}:
                action = "view"
            elif last_ev == "view":
                action = "add_to_cart" if goal == "buy" else "add_to_wishlist"
            elif last_ev == "add_to_wishlist":
                # Drive more searches in browsing sessions.
                action = "search"
            elif last_ev == "add_to_cart":
                # Ensure remove_from_cart exists in easy dataset: remove once per session
                # when we have enough remaining steps; then add again.
                if (not did_remove) and len(cart) > 0 and remaining >= 4:
                    action = "remove_from_cart"
                else:
                    # Keep checkout/purchase less frequent overall by delaying checkout
                    # until later steps in the session.
                    if goal == "buy" and (not checkout_started) and remaining > 5:
                        action = "search"
                    else:
                        action = "checkout_start" if not checkout_started else "purchase"
            elif last_ev == "remove_from_cart":
                action = "view"
            elif last_ev == "checkout_start":
                action = "purchase"
            else:
                action = "view"
        else:
            action = ""

        # If goal is buy, steer to checkout near the end.
        if goal == "buy" and remaining <= 3:
            if cart and not checkout_started:
                events.append(
                    {
                        "event_type": "checkout_start",
                        "page": "checkout",
                        "product_id": "",
                        "query_text": "",
                        "duration_ms": str(random.randint(2000, 12000)),
                        "product_type": "LAPTOP",
                    }
                )
                checkout_started = True
                continue
            if cart and checkout_started:
                # Purchase the most recently viewed/cart item.
                purchase_pid = cart[-1] if cart else (last_viewed or _pick_product_for_user(profile, product_ids))
                events.append(
                    {
                        "event_type": "purchase",
                        "page": "checkout_success",
                        "product_id": str(purchase_pid),
                        "query_text": "",
                        "duration_ms": str(random.randint(4000, 15000)),
                        "product_type": "LAPTOP",
                    }
                )
                break

        if difficulty != "easy" and goal == "support" and profile.chat_prone and random.random() < 0.45:
            # More chat events; often about last viewed.
            pid = last_viewed or _pick_product_for_user(profile, product_ids)
            last_viewed = pid
            events.append(
                {
                    "event_type": "chat",
                    "page": "chat_widget",
                    "product_id": str(pid),
                    "query_text": random.choice(CHAT_TEXTS),
                    "duration_ms": "",
                    "product_type": "LAPTOP",
                }
            )
            continue

        if not action:
            # Choose next action based on current state (realistic mode)
            candidates: list[str] = []
            weights: list[float] = []

            # Browsing actions
            candidates += ["view", "filter", "sort"]
            weights += [0.45, 0.20, 0.20]

            # paginate is replaced by add_to_wishlist (needs a product; prefer after view)
            if last_viewed is not None:
                candidates += ["add_to_wishlist"]
                weights += [0.12]

            # Search occasionally
            candidates += ["search"]
            weights += [0.10]

            # Cart actions depend on cart state
            if last_viewed is not None:
                candidates += ["add_to_cart"]
                weights += [0.18 if goal in {"buy", "abandon"} else 0.10]

            if cart:
                candidates += ["remove_from_cart"]
                weights += [0.12 if goal == "abandon" else 0.05]

            if cart and not checkout_started and goal == "buy":
                candidates += ["checkout_start"]
                weights += [0.10]

            # Normalize not required for random.choices
            action = random.choices(candidates, weights=weights, k=1)[0]

        if action == "view":
            pid = _pick_product_for_user(profile, product_ids)
            last_viewed = pid
            events.append(
                {
                    "event_type": "view",
                    "page": "product_detail",
                    "product_id": str(pid),
                    "query_text": "",
                    "duration_ms": str(random.randint(18000, 75000)),
                    "product_type": "LAPTOP",
                }
            )
        elif action == "add_to_wishlist":
            pid = last_viewed or _pick_product_for_user(profile, product_ids)
            last_viewed = pid
            events.append(
                {
                    "event_type": "add_to_wishlist",
                    "page": "wishlist",
                    "product_id": str(pid),
                    "query_text": "",
                    "duration_ms": str(random.randint(600, 2500)),
                    "product_type": "LAPTOP",
                }
            )
        elif action == "filter":
            events.append(
                {
                    "event_type": "filter",
                    "page": "products_list",
                    "product_id": "",
                    "query_text": _filter_text_for_user(profile),
                    "duration_ms": "",
                    "product_type": "LAPTOP",
                }
            )
        elif action == "sort":
            events.append(
                {
                    "event_type": "sort",
                    "page": "products_list",
                    "product_id": "",
                    "query_text": random.choice(SORT_TEXTS),
                    "duration_ms": "",
                    "product_type": "LAPTOP",
                }
            )
        elif action == "search":
            events.append(
                {
                    "event_type": "search",
                    "page": "products_list",
                    "product_id": "",
                    "query_text": _build_search_query(profile, search_queries),
                    "duration_ms": "",
                    "product_type": "LAPTOP",
                }
            )
        elif action == "add_to_cart":
            # Enforce constraint: add_to_cart needs a product (prefer last viewed)
            pid = last_viewed if last_viewed is not None and random.random() < 0.8 else _pick_product_for_user(profile, product_ids)
            cart.append(pid)
            events.append(
                {
                    "event_type": "add_to_cart",
                    "page": "cart",
                    "product_id": str(pid),
                    "query_text": "",
                    "duration_ms": str(random.randint(1500, 9000)),
                    "product_type": "LAPTOP",
                }
            )
        elif action == "remove_from_cart":
            if not cart:
                continue
            pid = cart.pop()  # remove most recent
            events.append(
                {
                    "event_type": "remove_from_cart",
                    "page": "cart",
                    "product_id": str(pid),
                    "query_text": "",
                    "duration_ms": str(random.randint(800, 6000)),
                    "product_type": "LAPTOP",
                }
            )
            did_remove = True
        elif action == "checkout_start":
            if not cart:
                continue
            checkout_started = True
            events.append(
                {
                    "event_type": "checkout_start",
                    "page": "checkout",
                    "product_id": "",
                    "query_text": "",
                    "duration_ms": str(random.randint(2000, 12000)),
                    "product_type": "LAPTOP",
                }
            )

        elif action == "purchase":
            # Enforce constraints: purchase only if checkout started and cart_size > 0.
            # If we're not in a valid state, emit the missing prerequisite event(s)
            # to guarantee progress and avoid infinite loops.
            if not cart:
                # No item to purchase: go back to viewing a product.
                pid = _pick_product_for_user(profile, product_ids)
                last_viewed = pid
                events.append(
                    {
                        "event_type": "view",
                        "page": "product_detail",
                        "product_id": str(pid),
                        "query_text": "",
                        "duration_ms": str(random.randint(18000, 75000)),
                        "product_type": "LAPTOP",
                    }
                )
                continue

            if not checkout_started:
                checkout_started = True
                events.append(
                    {
                        "event_type": "checkout_start",
                        "page": "checkout",
                        "product_id": "",
                        "query_text": "",
                        "duration_ms": str(random.randint(2000, 12000)),
                        "product_type": "LAPTOP",
                    }
                )
                continue

            pid = cart.pop()  # purchase most recent cart item
            last_viewed = pid
            events.append(
                {
                    "event_type": "purchase",
                    "page": "checkout_success",
                    "product_id": str(pid),
                    "query_text": "",
                    "duration_ms": str(random.randint(4000, 15000)),
                    "product_type": "LAPTOP",
                }
            )
            checkout_started = False

        # Add optional chat after a view/add (only in realistic mode)
        if difficulty != "easy" and profile.chat_prone and last_viewed is not None and random.random() < 0.12:
            events.append(
                {
                    "event_type": "chat",
                    "page": "chat_widget",
                    "product_id": str(last_viewed),
                    "query_text": random.choice(CHAT_TEXTS),
                    "duration_ms": "",
                    "product_type": "LAPTOP",
                }
            )

        # If abandon goal, sometimes leave after removing items
        if difficulty != "easy" and goal == "abandon" and not cart and len(events) >= int(max_events * 0.6) and random.random() < 0.35:
            break

    # Stitch timestamps and add session-local indexing/feature columns
    stitched: list[dict[str, str]] = []
    prev_dt: datetime | None = None
    for idx, e in enumerate(events, start=1):
        if prev_dt is None:
            dt = current_dt
            gap_s = 0
        else:
            dt, gap_s = _advance_time(prev_dt, profile)
        prev_dt = dt
        stitched.append(
            {
                **e,
                "session_id": session_id,
                "created_at": _iso_z(dt),
                "time_since_prev_s": str(gap_s),
                "session_event_index": str(idx),
            }
        )

    return stitched


def _parse_start_dt(value: str) -> datetime:
    # Accept: YYYY-MM-DD or ISO8601 with Z
    if value.endswith("Z"):
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    if "T" in value:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    dt = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return dt


def _load_product_ids(product_nodes_csv: Path) -> list[int]:
    product_ids: list[int] = []
    with product_nodes_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = (row.get("product_id") or "").strip()
            if not pid:
                continue
            try:
                product_ids.append(int(pid))
            except ValueError:
                continue

    if not product_ids:
        raise ValueError(f"No product_id found in {product_nodes_csv}")

    return sorted(set(product_ids))


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate fake interaction CSV data for Neo4j import. "
            "Produces 10 different behaviors per user by default."
        )
    )
    parser.add_argument("--users", type=int, default=500)
    parser.add_argument("--events-per-user", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--start", type=str, default="2026-04-01")
    parser.add_argument(
        "--difficulty",
        type=str,
        default="realistic",
        choices=["easy", "realistic"],
        help=(
            "easy: highly predictable sequences (accuracy can be >0.6); "
            "realistic: more branching/noise (harder)."
        ),
    )
    parser.add_argument(
        "--out",
        type=str,
        default=str(Path(__file__).with_name("data_user500.csv")),
    )
    parser.add_argument(
        "--products",
        type=str,
        default=str(Path(__file__).with_name("product_nodes.csv")),
    )
    args = parser.parse_args()

    if args.users <= 0:
        raise SystemExit("--users must be > 0")
    if args.events_per_user <= 0:
        raise SystemExit("--events-per-user must be > 0")

    random.seed(args.seed)

    # Build richer query lists after seeding (reproducible).
    search_queries = list(BASE_SEARCH_QUERIES)
    search_queries += [
        f"laptop {random.choice(BRANDS).lower()} {random.choice(BUDGETS)}" for _ in range(15)
    ]
    search_queries += [
        f"laptop {random.choice(CPU_KEYWORDS)} {random.choice(BUDGETS)}" for _ in range(15)
    ]
    search_queries += [
        f"laptop {random.choice(GPU_KEYWORDS)} {random.choice(BUDGETS)}" for _ in range(15)
    ]

    product_ids = _load_product_ids(Path(args.products))
    start_dt = _parse_start_dt(args.start)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    headers = [
        "event_id",
        "user_id",
        "session_id",
        "event_type",
        "product_id",
        "query_text",
        "duration_ms",
        "created_at",
        "page",
        "product_type",
        # extra basic features (safe to ignore in downstream)
        "time_since_prev_s",
        "session_event_index",
        "device",
        "referrer",
        "preferred_brand",
        "preferred_budget",
        "preferred_purpose",
        "cart_size",
    ]

    event_seq = 1

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()

        for user_idx in range(1, args.users + 1):
            profile = _make_user_profile(user_idx)

            # 1-3 sessions per user
            sessions_count = random.randint(1, 3)
            user_base_dt = start_dt + timedelta(
                days=random.randint(0, 20),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )

            # Split events across sessions with mild variability
            remaining = args.events_per_user
            session_event_budgets: list[int] = []
            for s in range(sessions_count):
                if s == sessions_count - 1:
                    session_event_budgets.append(remaining)
                else:
                    # keep at least 8 events per session when possible
                    min_left = 8 * (sessions_count - s - 1)
                    budget = random.randint(8, max(8, remaining - min_left))
                    session_event_budgets.append(budget)
                    remaining -= budget

            current_dt = user_base_dt
            cart_size = 0
            for session_no, budget in enumerate(session_event_budgets, start=1):
                session_id = f"SSN_{profile.user_id}_{session_no:02d}"
                session_events = _generate_session_events(
                    profile=profile,
                    session_id=session_id,
                    start_dt=current_dt,
                    product_ids=product_ids,
                    search_queries=search_queries,
                    max_events=budget,
                    difficulty=args.difficulty,
                )

                # Estimate cart size over time for a basic feature
                # (not perfectly accurate across sessions, but gives a consistent signal)
                for e in session_events:
                    if e["event_type"] == "add_to_cart":
                        cart_size += 1
                    elif e["event_type"] == "remove_from_cart" and cart_size > 0:
                        cart_size -= 1
                    elif e["event_type"] == "purchase" and cart_size > 0:
                        cart_size -= 1

                    writer.writerow(
                        {
                            "event_id": f"EVT_{event_seq:06d}",
                            "user_id": profile.user_id,
                            "session_id": e["session_id"],
                            "event_type": e["event_type"],
                            "product_id": e["product_id"],
                            "query_text": e["query_text"],
                            "duration_ms": e["duration_ms"],
                            "created_at": e["created_at"],
                            "page": e["page"],
                            "product_type": e["product_type"],
                            "time_since_prev_s": e["time_since_prev_s"],
                            "session_event_index": e["session_event_index"],
                            "device": profile.device,
                            "referrer": profile.referrer,
                            "preferred_brand": profile.preferred_brand,
                            "preferred_budget": profile.preferred_budget,
                            "preferred_purpose": profile.preferred_purpose,
                            "cart_size": str(cart_size),
                        }
                    )
                    event_seq += 1

                # advance base time between sessions by 10-180 minutes
                current_dt = current_dt + timedelta(minutes=random.randint(10, 180))

    print(f"Wrote {event_seq - 1} events to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
