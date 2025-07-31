from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, validator
from datetime import datetime
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

router = APIRouter()


class BookingRequest(BaseModel):
    login_id: str
    login_pw: str
    month: int
    day: int
    start_time: str
    end_time: str    
    room: str
    id: int
    day_of_week: str


    @validator("month", "day", pre=True)
    def convert_to_int(cls, v):
        return int(v)


# --- API Route ---

@router.post("/book")
def book_slot(data: BookingRequest):
    try:
        session = requests.Session()

        login_data = {
            "loginid": data.login_id,
            "loginpw": data.login_pw,
            "calendar": "1",
            "login_direct_id": "0",
            "login_direct_calendar_id": "0",
            "submit": "Log in"
        }

        login_url = "https://jptraining.resv.jp/user/usr_login.php"
        session.post(login_url, data=login_data)

        # Check login success
        mypage = session.get("https://jptraining.resv.jp/user/res_user.php?calendar=1")
        if 'ログインID' in mypage.text or 'Login ID' in mypage.text:
            raise HTTPException(status_code=401, detail="Login failed")

        calendar_url = "https://jptraining.resv.jp/reserve/calendar.php"
        session.get(calendar_url, headers={"Referer": login_url, "User-Agent": "Mozilla/5.0"})

        date = datetime(year=2025, month=data.month, day=data.day)
        html = get_timetable(session, date.year, date.month, date.day, calendar_url)
        slots = extract_timetable(html, data.start_time, data.end_time)

        filtered_slots = [s for s in slots if s["room"] == data.room and s["remain"] > 0]
        if not filtered_slots:
            raise HTTPException(status_code=404, detail="No available slots for selected time and room")

        slot = filtered_slots[0]
        detail_url = urljoin(calendar_url, slot["detail_url"])
        resp = submit_next_form(session, detail_url)

        confirm_url = extract_confirm_url(resp.text, resp.url)
        if not confirm_url:
            raise HTTPException(status_code=500, detail="Failed to get confirmation form")

        result = complete_reservation(session, confirm_url)
        if result["status"] != "success":
            raise HTTPException(status_code=500, detail=result["message"])

        return {"status": "success", "message": "Booking successful"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Helpers ---

def get_timetable(session, year, month, day, calendar_url):
    base_url = "https://jptraining.resv.jp/reserve/get_timetable_pc.php"
    params = {
        "view_mode": "day",
        "view_list": "0",
        "relation_mp": "1",
        "cur_year": year,
        "cur_month": month,
        "cur_day": day,
        "cur_mp_id": "0",
        "_": int(time.time() * 1000),
    }
    headers = {
        "Referer": calendar_url,
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
    }
    r = session.get(base_url, params=params, headers=headers)
    r.raise_for_status()
    return r.text


def extract_timetable(html, desired_start, desired_end):
    soup = BeautifulSoup(html, 'html.parser')
    results = []

    for lesson_div in soup.select('div.lesson'):
        time_a = lesson_div.select_one('li.data-week-info a')
        room_a = lesson_div.select_one('li.data-week-mp-name a')
        remain_span = lesson_div.select_one('span.zannsu')

        timestr = None
        if time_a:
            for part in time_a.contents:
                if isinstance(part, str) and '-' in part:
                    timestr = part.strip()
            if not timestr:
                lines = time_a.get_text("\n").splitlines()
                lines = [l.strip() for l in lines if '-' in l]
                timestr = lines[-1] if lines else '?'

        if timestr and "-" in timestr:
            start, end = timestr.split('-')
            if start.strip() >= desired_start and end.strip() <= desired_end:
                remain = int(''.join(filter(str.isdigit, remain_span.text))) if remain_span else 0
                if remain > 0:
                    detail_url = time_a.get('href')
                    results.append({
                        "time": timestr,
                        "room": room_a.text.strip() if room_a else '',
                        "remain": remain,
                        "detail_url": detail_url
                    })
    return results


def submit_next_form(session, detail_url):
    r = session.get(detail_url)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')

    form = soup.find("form")
    if not form:
        raise Exception("No form found on detail page")

    action = form.get("action")
    form_url = urljoin(detail_url, action) if action else detail_url

    form_data = {}
    for input_tag in form.find_all("input"):
        input_type = input_tag.get("type", "").lower()
        name = input_tag.get("name")
        value = input_tag.get("value", "")
        if input_type == "submit" and value.strip() != "Proceed to the next":
            continue
        if name:
            form_data[name] = value

    form_data["submit"] = "Proceed to the next"

    response = session.post(form_url, data=form_data)
    response.raise_for_status()
    return response


def extract_confirm_url(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    form = soup.find("form")
    if not form:
        return None
    action = form.get("action")
    return urljoin(base_url, action) if action else None


def complete_reservation(session, confirm_url):
    r = session.get(confirm_url)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, 'html.parser')
    form = soup.find("form")
    if not form:
        return {"status": "error", "message": "No form found on confirmation page"}

    action = form.get("action")
    form_url = urljoin(confirm_url, action) if action else confirm_url

    form_data = {}
    for input_tag in form.find_all("input"):
        name = input_tag.get("name")
        value = input_tag.get("value", "")
        if name:
            form_data[name] = value

    form_data["submit1"] = "complete"

    response = session.post(form_url, data=form_data)
    response.raise_for_status()

    if "予約完了" in response.text or "Reservation Complete" in response.text:
        return {"status": "success", "message": "Reservation completed successfully"}

    return {"status": "error", "message": "Unknown result – check HTML", "html": response.text}
