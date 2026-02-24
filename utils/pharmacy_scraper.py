"""Парсинг дежурных аптек с сайта."""

import re
from urllib import request as urlrequest


def fetch_live_duty_pharmacies() -> list[tuple[str, str, str | None]]:
    """Получить список дежурных аптек с сайта cyprus.ondutypharmacy.com.
    
    Returns:
        Список кортежей (название, телефон, адрес)
        
    Raises:
        RuntimeError: Если не удалось получить данные
    """
    candidate_urls = [
        "https://cyprus.ondutypharmacy.com/limassol/",
        "https://cyprus.ondutypharmacy.com/limassol/all-pharmacies/",
    ]
    html = ""
    last_error: Exception | None = None
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
    }

    for url in candidate_urls:
        try:
            req = urlrequest.Request(url, headers=headers)
            html = urlrequest.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
            if html:
                break
        except Exception as exc:
            last_error = exc
            continue

    if not html:
        if last_error:
            raise last_error
        raise RuntimeError("Unable to fetch duty pharmacies")

    items = re.findall(
        r'<div class="col-md-6 mb-15 pharmacy-card"><div class="pharmacy-box">(.*?)</div></div>',
        html,
        re.S | re.I,
    )
    result: list[tuple[str, str, str | None]] = []
    for block in items:
        name_match = re.search(r"<a [^>]*>(.*?)</a>", block, re.S | re.I)
        phone_match = re.search(r'href="tel:([^"]+)"', block, re.S | re.I)
        if not name_match or not phone_match:
            continue

        raw_name = re.sub("<.*?>", "", name_match.group(1)).strip()
        raw_phone = "".join(ch for ch in phone_match.group(1) if ch.isdigit())
        if len(raw_phone) < 8:
            continue
        phone = f"+357 {raw_phone[-8:]}"

        block_text = re.sub("<.*?>", " ", block)
        block_text = " ".join(block_text.split())
        address_match = re.search(r"</span>(.*?)<b>", block, re.S | re.I)
        address: str | None = None
        if address_match:
            address = " ".join(re.sub("<.*?>", " ", address_match.group(1)).split())
            if not address:
                address = None
        elif block_text:
            address = block_text

        result.append((raw_name, phone, address))

    return result


def extract_rating(notes: str | None) -> float | None:
    """Извлечь рейтинг из примечаний сервиса.
    
    Args:
        notes: Примечания сервиса
        
    Returns:
        Рейтинг или None если не найден
    """
    if not notes:
        return None
    m = re.search(r"Google rating:\s*([0-9.]+)", notes)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None
