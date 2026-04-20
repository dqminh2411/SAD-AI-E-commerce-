import argparse
import csv
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


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
    Behavior("paginate", page="products_list", duration_ms_range=(800, 3500)),
    Behavior("add_to_cart", page="cart", needs_product=True, duration_ms_range=(1500, 9000)),
    Behavior("remove_from_cart", page="cart", needs_product=True, duration_ms_range=(800, 6000)),
    Behavior("checkout_start", page="checkout", duration_ms_range=(2000, 12000)),
    Behavior("purchase", page="checkout_success", needs_product=True, duration_ms_range=(4000, 15000)),
    Behavior("chat", page="chat_widget", needs_text=True),
]

BRANDS = ["ASUS", "Lenovo", "Acer", "Dell", "HP", "MSI"]
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
    parser.add_argument("--events-per-user", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--start", type=str, default="2026-04-01")
    parser.add_argument(
        "--out",
        type=str,
        default=str(Path(__file__).with_name("fake_interactions.csv")),
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
    ]

    event_seq = 1

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()

        for user_idx in range(1, args.users + 1):
            user_id = f"US_{user_idx:03d}"

            # 1-3 sessions per user
            sessions_count = random.randint(1, 3)
            user_base_dt = start_dt + timedelta(
                days=random.randint(0, 20),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )

            # Spread events across sessions.
            behaviors = BEHAVIORS.copy()
            random.shuffle(behaviors)

            # If user asks for more/less than 10, just cycle.
            total_events = args.events_per_user
            behavior_list = [behaviors[i % len(behaviors)] for i in range(total_events)]

            current_dt = user_base_dt
            for i, behavior in enumerate(behavior_list):
                session_no = (i % sessions_count) + 1
                session_id = f"SSN_{user_id}_{session_no:02d}"

                product_id: str | None = ""
                query_text: str | None = ""
                duration_ms: str | None = ""

                if behavior.needs_product:
                    product_id = str(random.choice(product_ids))

                if behavior.needs_text:
                    if behavior.event_type == "search":
                        query_text = random.choice(search_queries)
                    elif behavior.event_type == "filter":
                        query_text = random.choice(FILTER_TEXTS)
                    elif behavior.event_type == "sort":
                        query_text = random.choice(SORT_TEXTS)
                    elif behavior.event_type == "chat":
                        # Often chat is about the last seen product if any.
                        if not product_id:
                            product_id = str(random.choice(product_ids))
                        query_text = random.choice(CHAT_TEXTS)
                    else:
                        query_text = behavior.event_type

                if behavior.duration_ms_range:
                    duration_ms = str(random.randint(*behavior.duration_ms_range))

                writer.writerow(
                    {
                        "event_id": f"EVT_{event_seq:06d}",
                        "user_id": user_id,
                        "session_id": session_id,
                        "event_type": behavior.event_type,
                        "product_id": product_id,
                        "query_text": query_text,
                        "duration_ms": duration_ms,
                        "created_at": _iso_z(current_dt),
                        "page": behavior.page,
                        "product_type": "LAPTOP",
                    }
                )

                event_seq += 1
                # advance time 10s-4m between events
                current_dt = current_dt + timedelta(seconds=random.randint(10, 240))

    print(f"Wrote {event_seq - 1} events to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
