import bcrypt
from dbconnect import db

class User(db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    # Security enhancements for brute-force defense and session invalidation
    is_locked = db.Column(db.Boolean, default=False)
    failed_attempts = db.Column(db.Integer, default=0)
    token_version = db.Column(db.Integer, default=1)

    # 1-to-1 Relationships to Profile Tables
    patient = db.relationship('Patient', backref='user', uselist=False, cascade='all, delete-orphan')
    doctor = db.relationship('Doctor', backref='user', uselist=False, cascade='all, delete-orphan')
    admin = db.relationship('Admin', backref='user', uselist=False, cascade='all, delete-orphan')

    def set_password(self, raw_password: str):
        """Hashes the password using bcrypt with a unique salt."""
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(raw_password.encode('utf-8'), salt).decode('utf-8')

    def check_password(self, raw_password: str) -> bool:
        """Performs a safe constant-time verification of the password."""
        if not self.password_hash:
            return False
        return bcrypt.checkpw(raw_password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def record_failed_attempt(self, max_attempts=5):
        """Increments the failed login count and locks the account if the threshold is met."""
        self.failed_attempts += 1
        if self.failed_attempts >= max_attempts:
            self.is_locked = True

    def reset_lockout(self):
        """Clears the failed login count and ensures the account is unlocked upon success."""
        self.failed_attempts = 0
        self.is_locked = False

    def to_dict(self):
        """Base serialization helper."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role,
            "is_locked": self.is_locked,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }