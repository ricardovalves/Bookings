from file import app, db, User

with app.app_context():
    # Drop all tables (optional - use this if you want to start fresh)
    db.drop_all()
    
    # Create all tables
    db.create_all()
    
    # Create admin user if it doesn't exist
    if not User.query.filter_by(is_admin=True).first():
        admin = User(
            email='admin@example.com',
            building='ADMIN',
            apartment='ADMIN',
            is_admin=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully!")
    
    print("Database initialized successfully!")