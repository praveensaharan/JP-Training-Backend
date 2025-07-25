
import traceback
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import requests
import time, os
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from db import get_connection
from routes.send_emails import send_subscription_email


router = APIRouter()

# Load credentials
load_dotenv()
userId = os.getenv("JP_ID")
password = os.getenv("JP_PASSWORD")

# HTML parsing helper
def extract_timetable(html):
    soup = BeautifulSoup(html, 'html.parser')
    results = []

    for timeline in soup.select('div.time-line'):
        time_a = timeline.select_one('li.data-week-info a')
        room_a = timeline.select_one('li.data-week-mp-name a')
        remain_span = timeline.select_one('span.zannsu')

        # Extract time range
        timestr = None
        if time_a:
            for part in time_a.contents:
                if isinstance(part, str) and '-' in part:
                    timestr = part.strip()
            if not timestr:
                lines = time_a.get_text("\n").splitlines()
                lines = [l.strip() for l in lines if '-' in l]
                timestr = lines[-1] if lines else '?'

        results.append({
            "time": timestr or '?',
            "room": room_a.text.strip() if room_a else '',
            "remain": int(''.join(filter(str.isdigit, remain_span.text))) if remain_span else 0,
        })

    return results

# Fetch timetable HTML
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
    return r.text

# Main sync endpoint
@router.get("/timetable/sync")
def sync_timetable():
    session = requests.Session()
    login_data = {
        "loginid": userId,
        "loginpw": password,
        "calendar": "1",
        "login_direct_id": "0",
        "login_direct_calendar_id": "0",
        "submit": "Log in"
    }

    # Step 1: Login
    login_url = "https://jptraining.resv.jp/user/usr_login.php"
    session.post(login_url, data=login_data)

    # Step 2: Verify login
    mypage = session.get("https://jptraining.resv.jp/user/res_user.php?calendar=1")
    if 'ログインID' in mypage.text or 'Login ID' in mypage.text:
        raise HTTPException(status_code=401, detail="Login failed")

    # Step 3: Navigate
    menu_url = "https://jptraining.resv.jp/user/usr_menu.php"
    session.get(menu_url)
    calendar_url = "https://jptraining.resv.jp/reserve/calendar.php"
    session.get(calendar_url, headers={"Referer": menu_url, "User-Agent": "Mozilla/5.0"})

    # Step 4: Loop through next 6 days
    today = datetime.today()
    summary = []
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Failed to connect to the database")

    try:
        with conn.cursor() as cursor:
            no_data_days = 0
            max_days = 70
            max_empty_days = 3
            for offset in range(max_days):
                date = today + timedelta(days=offset)
                html = get_timetable(session, date.year, date.month, date.day, calendar_url)
                slots = extract_timetable(html)
                if not slots:
                    no_data_days += 1
                    print(f"No data found for {date.date()} (empty count: {no_data_days})")
                    if no_data_days >= max_empty_days:
                        print("No data found for 3 consecutive days. Stopping early.")
                        break
                    continue  # skip DB operation for this date
                else:
                    no_data_days = 0

                for slot in slots:
                    # Parse start/end time
                    if slot["time"] and '-' in slot["time"]:
                        try:
                            start_str, end_str = slot["time"].split('-')
                            start_time = datetime.strptime(start_str.strip(), "%H:%M").time()
                            end_time = datetime.strptime(end_str.strip(), "%H:%M").time()
                        except Exception:
                            continue
                    else:
                        continue  # skip malformed entries

                    # Check if already exists
                    cursor.execute(
                        """
                       SELECT id FROM schedules
                       WHERE date = %s AND starttime = %s AND endtime = %s AND room = %s
                        """,
                        (date.date(), start_time, end_time, slot["room"])
                    )
                    existing = cursor.fetchone()

                    if existing is not None:
                        schedule_id = existing["id"] if isinstance(existing, dict) else existing[0]
                        print(f"Existing entry: {existing}")

                        print(f"Inserting: {date.date()} | {start_time}-{end_time} | {slot['room']} | {slot['remain']}")

                        # Update
                        cursor.execute(
                            """
                            UPDATE schedules
                            SET room = %s, remain = %s
                            WHERE id = %s
                            """,
                            (slot["room"], slot["remain"], schedule_id)
                        )
                    else:
                        # Insert
                        print(f"Inserting: {date.date()} | {start_time}-{end_time} | {slot['room']} | {slot['remain']}")

                        cursor.execute(
                            """
                            INSERT INTO schedules (date, starttime, endtime, room, remain)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (date.date(), start_time, end_time, slot["room"], slot["remain"])
                        )

                summary.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "count": len(slots)
                })

            conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error:\n{traceback.format_exc()}")
    finally:
        conn.close()

    send_subscription_email()

    return {
        "status": "success",
        "updated_dates": summary
    }
