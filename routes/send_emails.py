from db import get_connection
from email_utils import send_email
from datetime import datetime
import traceback
from fastapi import APIRouter, HTTPException

def send_subscription_email():
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Failed to connect to the database")

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT date, starttime, endtime, room, remain 
                FROM schedules 
                WHERE remain > 0 AND date > CURRENT_DATE + INTERVAL '1 day'
                ORDER BY date, starttime
            """)
            slots = cursor.fetchall()
            print(f"Found {len(slots)} available slots.")

            if not slots:
                print("No available slots with remaining spots.")
                return
            

            subject = "JP Training - Available Slots Notification"

            cursor.execute("SELECT email FROM emails")
            emails = cursor.fetchall()
            print(f"Found {len(emails)} subscribers.", emails)
            email_list = [row["email"] for row in emails]


            for email in email_list:
                unsubscribe_url = f"https://jp-training.vercel.app/unsubscribe?email={email}"
                body = make_email_body_html(slots, unsubscribe_url=unsubscribe_url)
                success = send_email(
                    to_email=email,
                    subject=subject,
                    body=body
                )
                if success:
                    print(f"Notification sent to {email}")
                else:
                    print(f"Failed to send to {email}")

    except Exception as e:
        print(f"Error while sending subscription emails: {e}")
        traceback.print_exc()

        raise HTTPException(status_code=500, detail="Error while sending subscription emails")

    finally:
        conn.close()


def make_email_body_html(slots, unsubscribe_url):
    def style_badge(remain):
        if remain <= 0:
            return "linear-gradient(135deg, #ff6b6b, #ee5a52)"
        elif remain <= 1:
            return "linear-gradient(135deg, #ffa726, #ff9800)"
        else:
            return "linear-gradient(135deg, #66bb6a, #4caf50)"

    rows_html = ""
    for row in slots:
        date = row["date"].strftime("%Y-%m-%d")
        start = row["starttime"].strftime("%H:%M")
        end = row["endtime"].strftime("%H:%M")
        room = row["room"]
        remain = row["remain"]
        badge_color = style_badge(remain)

        rows_html += f"""
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.15); transition: background-color 0.3s ease;">
                <td style="padding: 16px 12px; text-align: left; font-weight: 500;">{date}</td>
                <td style="padding: 16px 12px; text-align: center; font-weight: 500;">{start} - {end}</td>
                <td style="padding: 16px 12px; text-align: center; font-weight: 500;">Room {room}</td>
                <td style="padding: 16px 12px; text-align: center;">
                    <span style="
                        background: {badge_color};
                        color: white;
                        padding: 6px 12px;
                        border-radius: 20px;
                        font-size: 12px;
                        font-weight: 600;
                        text-shadow: 0 1px 2px rgba(0,0,0,0.2);
                    ">{remain} spots left</span>
                </td>
            </tr>
        """

    body = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Training Slots Available</title>
</head>
<body style="
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  margin: 0;
  padding: 40px 20px;
  color: #ffffff;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  line-height: 1.6;
">
  <div style="max-width: 600px; margin: 0 auto;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="
      background: rgba(255, 255, 255, 0.1);
      backdrop-filter: blur(10px);
      border-radius: 24px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.3);
      border: 1px solid rgba(255,255,255,0.2);
      margin-bottom: 20px;
    ">
      <tr>
        <td style="padding: 40px 30px; text-align: center;">
          
          <div style="
                  width: 64px; 
                  height: 64px; 
                  margin: auto; 
                  background: linear-gradient(135deg, #9f7aea, #22d3ee); 
                  border-radius: 16px; 
                  box-shadow: 0 0 15px 3px rgba(159,122,234,0.6);
                  display: flex; 
                  align-items: center; 
                  justify-content: center;">
                <img 
                  src="https://img.freepik.com/premium-vector/sparkle-design-bundle-sparkle-stars-bright-stars-twinkle-stars_1045590-1549.jpg" 
                  width="40" 
                  height="40" 
                  style="border-radius: 20%; 
                        display: block;  
                        filter: drop-shadow(0 0 2px rgba(255,255,255,0.6));" 
                  alt="Icon"
                />
              </div>

          <p style="
            font-size: 14px;
            line-height: 1.5;
            margin: 0 1 8px;
            opacity: 0.9;
            font-weight: 400;
          ">
            Reserve your spot in our upcoming training sessions
          </p>

          <div style="
            display: inline-block;
            background: linear-gradient(135deg, #00b894, #00a085);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 30px;
            box-shadow: 0 4px 12px rgba(0,184,148,0.3);
          ">
            ✨ {len(slots)} Sessions Available
          </div>
        </td>
      </tr>

      <tr>
        <td style="padding: 30px;">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="
            border-collapse: collapse;
            color: #ffffff;
            font-size: 14px;
            border-radius: 16px;
            background: rgba(255,255,255,0.05);
          ">
            <thead>
              <tr style="background: linear-gradient(135deg, rgba(255,255,255,0.2), rgba(255,255,255,0.1)); border-bottom: 2px solid rgba(255,255,255,0.3);">
                <th style="padding: 20px 12px; text-align: left; font-weight: 700; font-size: 16px;"> Date</th>
                <th style="padding: 20px 12px; text-align: center; font-weight: 700; font-size: 16px;">Time</th>
                <th style="padding: 20px 12px; text-align: center; font-weight: 700; font-size: 16px;"> Room</th>
                <th style="padding: 20px 12px; text-align: center; font-weight: 700; font-size: 16px;"> Availability</th>
              </tr>
            </thead>
            <tbody>
              {rows_html}
            </tbody>
          </table>
        </td>
      </tr>


      <tr>
        <td style="padding: 30px; text-align: center;">
          <a href="{unsubscribe_url}" style="
            color: rgba(255,255,255,0.6) !important;
            text-decoration: none;
            font-size: 12px;
            border-bottom: 1px solid rgba(255,255,255,0.3);
            transition: all 0.3s ease;">Unsubscribe from these notifications</a>
        </td>
      </tr>
    </table>
  </div>
</body>
</html>
"""
    return body
