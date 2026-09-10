import secrets
from database import SessionLocal
from models import Cat

def seed():
    db = SessionLocal()
    try:
        # Check if the Cat table is empty
        count = db.query(Cat).count()
        if count > 0:
            print(f"Cat table is not empty (found {count} rows). Skipping seed.")
            return

        print("Seeding cats into the database...")
        cats_to_insert = []
        
        # Array of placeholder Thai names
        placeholder_names = [
            "น้องบัญชี", 
            "น้อง HR", 
            "น้อง IT", 
            "น้อง Sales", 
            "น้อง Safety", 
            "น้องโรงงาน", 
            "น้อง QC", 
            "น้อง Lab", 
            "น้อง Sustain", 
            "น้อง Supply Chain"
        ]
        
        # Hardcoded tokens so that existing QR codes remain valid
        hardcoded_tokens = [
            'xs3fEj7P-abpXpOaoDUhMw', '7pgZeIiLviskiazBYzQarw', 'sAU4ljjMwY_gdRkvtqgKDw',
            'r85KCTQZHe_8pjAKvsQh-A', 'RH3YUqtQkQJ89pmf_2VK-g', 'kBc4a2ioOZSggSbUdXq6yQ',
            'qzr1OYl_D02u5GQ8Bs3URw', 'EFyPWX_Gil3foBCwZ9j7pA', 'BxN4R3wYY_g0IhuvsfvLRw',
            's4WszdCfECBCog70eXPQgg'
        ]
        
        for i in range(1, 11):
            cat_id = f"CAT{i:02d}"
            name = placeholder_names[i - 1]
            token = hardcoded_tokens[i - 1]
            
            cat = Cat(cat_id=cat_id, name=name, token=token, is_active=True)
            cats_to_insert.append(cat)
            
            # Print the data so the user can use the tokens for QR codes
            print(f"ID: {cat_id} | Name: {name} | Token: {token}")
            
        db.add_all(cats_to_insert)
        db.commit()
        print("\nSuccessfully seeded 10 cats!")
        
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
