from src.config import db


class UserCardSettings(db.Model):
    __tablename__ = "user_card_settings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    # Card Toggles
    is_user_card_enabled = db.Column(db.Boolean, default=True)
    is_server_card_enabled = db.Column(db.Boolean, default=True)
    is_battery_card_enabled = db.Column(db.Boolean, default=True)
    is_cpu_core_card_enabled = db.Column(db.Boolean, default=True)
    is_cpu_usage_card_enabled = db.Column(db.Boolean, default=True)
    is_cpu_temp_card_enabled = db.Column(db.Boolean, default=True)
    is_dashboard_memory_card_enabled = db.Column(db.Boolean, default=True)
    is_memory_usage_card_enabled = db.Column(db.Boolean, default=True)
    is_disk_usage_card_enabled = db.Column(db.Boolean, default=True)
    is_system_uptime_card_enabled = db.Column(db.Boolean, default=True)
    is_network_statistic_card_enabled = db.Column(db.Boolean, default=True)
    is_speedtest_enabled = db.Column(db.Boolean, default=True)