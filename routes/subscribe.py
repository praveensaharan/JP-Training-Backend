from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from email_utils import send_email
from routes.emails import insert_email

router = APIRouter()

class SubscribeRequest(BaseModel):
    email: EmailStr

@router.post("/subscribe")
def subscribe(req: SubscribeRequest):
    insert_email(req.email)
    subject = "Thanks for Subscribing to JP Training!"
    unsubscribe_url = f"https://jp-training.vercel.app/unsubscribe?email={req.email}"
    
    body = f"""
    <html>
      <body style="
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
        background: linear-gradient(135deg, #7e5bef, #0bc5ea);
        margin: 0; 
        padding: 40px 20px; 
        color: #fff;
        -webkit-font-smoothing: antialiased;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width: 600px; margin: auto; background: rgba(255, 255, 255, 0.1); border-radius: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
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

              <h2 style="font-size: 28px; margin: 20px 0 10px; font-weight: 700; letter-spacing: -0.02em;">
                You're now subscribed! 
              </h2>
              
              <p style="font-size: 16px; line-height: 1.5; margin: 0 0 40px;">
                Thanks for subscribing! We'll notify you as soon as slots become available.
              </p>
              
              <a href="{unsubscribe_url}" style="
                display: inline-block;
                background: linear-gradient(135deg, #e53e3e, #c53030);
                color: white !important;
                text-decoration: none;
                padding: 14px 24px;
                border-radius: 24px;
                font-weight: 600;
                font-size: 16px;
                box-shadow: 0 4px 12px rgba(197,48,48,0.6);
                transition: background-color 0.3s ease;"
                target="_blank" rel="noopener noreferrer">
                Unsubscribe
              </a>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """

    success = send_email(
        to_email=req.email,
        subject=subject,
        body=body
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send subscription email.")

    return {"message": "Subscribed successfully!"}
