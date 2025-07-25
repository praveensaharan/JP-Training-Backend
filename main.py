from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.subscribe import router as subscribe_router
from routes.unsubscribe import router as unsubscribe_router
from routes.timetable import router as timetable_router
from routes.emails import router as emails_router  # <-- new import
from routes.send_emails import send_subscription_email  # <-- new import

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(subscribe_router)
app.include_router(unsubscribe_router)
app.include_router(timetable_router)
app.include_router(emails_router)  # <-- new router



# This endpoint is for testing purposes
@app.get("/health")
def health_check():
    send_subscription_email()
    return {"status": "ok", "message": "API is running smoothly!"}
    
    
@app.get("/")
def root():
    return {"message": "Welcome to the JP Training API!"}
