from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from datetime import datetime, timedelta
import secrets

app = Flask(__name__)
app.config.update(
    SECRET_KEY='your-secret-key-here',  # Change this in production
    SQLALCHEMY_DATABASE_URI='sqlite:///partyroom.db',
    MAIL_SERVER='smtp.gmail.com',  # Change according to your email provider
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='your-email@gmail.com',  # Change this
    MAIL_PASSWORD='your-app-password',  # Change this (use app-specific password)
    MAIL_DEFAULT_SENDER='your-email@gmail.com'  # Change this
)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)  # Changed from password to password_hash
    building = db.Column(db.String(12), nullable=False)
    apartment = db.Column(db.String(10), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    bookings = db.relationship('Booking', backref='user', lazy=True)
    reset_token = db.Column(db.String(100), unique=True)
    reset_token_expiry = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def generate_reset_token(self):
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()
        return self.reset_token

    def verify_reset_token(self, token):
        if (self.reset_token != token or 
            self.reset_token_expiry is None or 
            self.reset_token_expiry < datetime.utcnow()):
            return False
        return True

    def clear_reset_token(self):
        self.reset_token = None
        self.reset_token_expiry = None
        db.session.commit()

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Add these validation functions
def validate_booking_time(start_time, end_time):
    now = datetime.now()
    
    # Basic time validations
    if start_time < now:
        return False, "Start time cannot be in the past"
    
    if end_time <= start_time:
        return False, "End time must be after start time"
    
    # Check if booking is within allowed hours (8 AM to 10 PM)
    if start_time.hour < 8 or end_time.hour > 22:
        return False, "Bookings are only allowed between 8 AM and 10 PM"
    
    # Check if duration is not more than 4 hours
    duration = end_time - start_time
    if duration > timedelta(hours=4):
        return False, "Bookings cannot exceed 4 hours"
    
    # Check if booking starts and ends on the same day
    if start_time.date() != end_time.date():
        return False, "Bookings must start and end on the same day"
    
    return True, ""

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    bookings = Booking.query.all()
    return render_template('dashboard.html', bookings=bookings)

@app.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    if request.method == 'POST':
        try:
            start_time = datetime.strptime(request.form.get('start_time'), '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(request.form.get('end_time'), '%Y-%m-%dT%H:%M')
            
            # Validate booking time
            is_valid, error_message = validate_booking_time(start_time, end_time)
            if not is_valid:
                flash(error_message)
                return redirect(url_for('book'))
            
            # Check for conflicts
            conflicts = Booking.query.filter(
                Booking.start_time < end_time,
                Booking.end_time > start_time,
                Booking.start_time.between(
                    start_time.replace(hour=0, minute=0),
                    start_time.replace(hour=23, minute=59)
                )
            ).first()
            
            if conflicts:
                flash('This time slot is already booked')
                return redirect(url_for('book'))
            
            # Create booking
            booking = Booking(
                user_id=current_user.id,
                start_time=start_time,
                end_time=end_time
            )
            db.session.add(booking)
            db.session.commit()
            flash('Booking created successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        except ValueError:
            flash('Invalid date format')
            return redirect(url_for('book'))
    
    # Get all bookings for calendar view
    all_bookings = Booking.query.all()
    bookings_json = [{
        'id': b.id,
        'title': f'Booked by {b.user.apartment}',
        'start': b.start_time.strftime('%Y-%m-%dT%H:%M'),
        'end': b.end_time.strftime('%Y-%m-%dT%H:%M'),
        'color': '#3498db' if b.user_id == current_user.id else '#2c3e50'
    } for b in all_bookings]
    
    return render_template('book.html', bookings=bookings_json)

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    users = User.query.all()
    return render_template('admin.html', users=users)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/create-admin', methods=['GET', 'POST'])
def create_admin():
    if User.query.filter_by(is_admin=True).first():
        return 'Admin already exists', 400
    
    admin = User(
        email='admin@example.com',  # Change this to your admin email
        building='ADMIN',
        apartment='ADMIN',
        is_admin=True
    )
    admin.set_password('admin123')  # Change this to your admin password
    
    db.session.add(admin)
    db.session.commit()
    
    return 'Admin created successfully'

@app.route('/add-tenant', methods=['POST'])
@login_required
def add_tenant():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.form
    
    # Check if email already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    # Create new tenant
    new_tenant = User(
        email=data['email'],
        building=data['building'],
        apartment=data['apartment'],
        is_admin=bool(data.get('isAdmin', False))
    )
    new_tenant.set_password(data['password'])  # You should generate a random password here
    
    db.session.add(new_tenant)
    db.session.commit()
    
    # Here you might want to send an email to the tenant with their credentials
    
    return jsonify({'message': 'Tenant added successfully'})

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = user.generate_reset_token()
            reset_url = url_for('reset_password', token=token, _external=True)
            
            try:
                msg = Message('Password Reset Request',
                             recipients=[user.email])
                msg.body = f'''To reset your password, visit the following link:
{reset_url}

If you did not make this request, please ignore this email.

This link will expire in 1 hour.
'''
                mail.send(msg)
                
                flash('Password reset instructions have been sent to your email.', 'info')
            except Exception as e:
                flash('Error sending email. Please try again later.', 'error')
                print(f"Email error: {str(e)}")  # For debugging
                
            return redirect(url_for('login'))
        
        flash('Email address not found.', 'error')
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or not user.verify_reset_token(token):
        flash('Invalid or expired reset token.', 'error')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('reset_password', token=token))
        
        user.set_password(password)
        user.clear_reset_token()
        
        flash('Your password has been updated!', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html')

@app.route('/delete-tenant/<int:user_id>', methods=['POST'])
@login_required
def delete_tenant(user_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting self
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot delete your own account'}), 400
        
    # Delete associated bookings first
    Booking.query.filter_by(user_id=user.id).delete()
    
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'message': 'Tenant deleted successfully'})

@app.route('/edit-tenant/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_tenant(user_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        data = request.get_json()
        
        # Check if email is being changed and if it's already taken
        if data['email'] != user.email and User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        user.email = data['email']
        user.building = data['building']
        user.apartment = data['apartment']
        user.is_admin = data['is_admin']
        
        if data.get('password'):  # Only update password if provided
            user.set_password(data['password'])
        
        db.session.commit()
        return jsonify({
            'message': 'Tenant updated successfully',
            'user': {
                'id': user.id,
                'email': user.email,
                'building': user.building,
                'apartment': user.apartment,
                'is_admin': user.is_admin
            }
        })
    
    return jsonify({
        'id': user.id,
        'email': user.email,
        'building': user.building,
        'apartment': user.apartment,
        'is_admin': user.is_admin
    })

if __name__ == '__main__':
    with app.app_context():
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
    app.run(debug=True, host='0.0.0.0', port=5000) 