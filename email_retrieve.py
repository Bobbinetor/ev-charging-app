from app import db
from app.models import Station

# 1) Usando query diretta su una colonna
emails = [email for (email,) in db.session.query(Station.email).all()]

# 2) Oppure caricando tutti gli oggetti Station
emails = [station.email for station in Station.query.all()]

print(emails)