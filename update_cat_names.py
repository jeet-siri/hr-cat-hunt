from database import SessionLocal
from models import Cat

def update_names():
    db = SessionLocal()
    try:
        names = {
            "CAT01": "น้องบัญชี",
            "CAT02": "น้อง HR",
            "CAT03": "น้อง IT",
            "CAT04": "น้อง Sales",
            "CAT05": "น้อง Safety",
            "CAT06": "น้องโรงงาน",
            "CAT07": "น้อง QC",
            "CAT08": "น้อง Lab",
            "CAT09": "น้อง Sustain",
            "CAT10": "น้อง Supply Chain"
        }
        
        for cat_id, new_name in names.items():
            cat = db.query(Cat).filter(Cat.cat_id == cat_id).first()
            if cat:
                cat.name = new_name
                print(f"Updated {cat_id} successfully")
            else:
                print(f"{cat_id} not found!")
                
        db.commit()
        print("Successfully updated all cat names!")
        
    except Exception as e:
        print(f"Error updating names: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_names()
