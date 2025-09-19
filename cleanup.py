from database import SessionLocal
import models

db = SessionLocal()

# Delete all users
db.query(models.User).delete()

# Commit changes
db.commit()

print(" All users deleted")
