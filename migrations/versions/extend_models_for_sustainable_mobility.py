"""extend_models_for_sustainable_mobility_hydrogen_support

Revision ID: f3a4b5c6d7e8
Revises: e2a7a7e77186
Create Date: 2025-01-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3a4b5c6d7e8'
down_revision = 'e2a7a7e77186'
branch_labels = None
depends_on = None


def upgrade():
    # Estendere tabella station per supporto multi-carburante
    op.add_column('station', sa.Column('fuel_types', sa.JSON(), nullable=True))
    op.add_column('station', sa.Column('station_type', sa.String(length=32), nullable=True))
    op.add_column('station', sa.Column('hydrogen_storage_capacity', sa.Float(), nullable=True))
    op.add_column('station', sa.Column('hydrogen_purity', sa.Float(), nullable=True))
    op.add_column('station', sa.Column('max_dispensing_pressure', sa.Integer(), nullable=True))
    
    # Aggiornare valori di default per stazioni esistenti
    op.execute("UPDATE station SET station_type = 'electric', fuel_types = '[\"electric\"]' WHERE station_type IS NULL")
    
    # Estendere tabella charging_point per supporto multi-carburante
    op.add_column('charging_point', sa.Column('fuel_type', sa.Enum('ELECTRIC', 'HYDROGEN', 'HYBRID', name='fueltype'), nullable=True))
    op.add_column('charging_point', sa.Column('connector_type', sa.Enum('TYPE2', 'CCS', 'CHADEMO', 'H70', 'H35', name='connectortype'), nullable=True))
    op.add_column('charging_point', sa.Column('voltage', sa.Float(), nullable=True))
    op.add_column('charging_point', sa.Column('current', sa.Float(), nullable=True))
    op.add_column('charging_point', sa.Column('dispensing_pressure', sa.Integer(), nullable=True))
    op.add_column('charging_point', sa.Column('flow_rate', sa.Float(), nullable=True))
    op.add_column('charging_point', sa.Column('temperature_range_min', sa.Float(), nullable=True))
    op.add_column('charging_point', sa.Column('temperature_range_max', sa.Float(), nullable=True))
    op.add_column('charging_point', sa.Column('purity_level', sa.Float(), nullable=True))
    op.add_column('charging_point', sa.Column('current_temperature', sa.Float(), nullable=True))
    op.add_column('charging_point', sa.Column('current_pressure', sa.Float(), nullable=True))
    op.add_column('charging_point', sa.Column('current_flow', sa.Float(), nullable=True))
    op.add_column('charging_point', sa.Column('last_telemetry_update', sa.DateTime(), nullable=True))
    
    # Aggiornare punti esistenti come elettrici
    op.execute("UPDATE charging_point SET fuel_type = 'ELECTRIC' WHERE fuel_type IS NULL")
    
    # Rendere fuel_type non nullable dopo l'aggiornamento
    op.alter_column('charging_point', 'fuel_type', nullable=False)
    
    # Estendere tabella charging_session per supporto multi-carburante
    op.add_column('charging_session', sa.Column('fuel_type', sa.Enum('ELECTRIC', 'HYDROGEN', 'HYBRID', name='fueltype'), nullable=True))
    op.add_column('charging_session', sa.Column('peak_power', sa.Float(), nullable=True))
    op.add_column('charging_session', sa.Column('average_power', sa.Float(), nullable=True))
    op.add_column('charging_session', sa.Column('hydrogen_dispensed', sa.Float(), nullable=True))
    op.add_column('charging_session', sa.Column('dispensing_pressure', sa.Integer(), nullable=True))
    op.add_column('charging_session', sa.Column('dispensing_temperature', sa.Float(), nullable=True))


def downgrade():
    # Rimuovere colonne aggiunte alle tabelle
    op.drop_column('charging_session', 'dispensing_temperature')
    op.drop_column('charging_session', 'dispensing_pressure')
    op.drop_column('charging_session', 'hydrogen_dispensed')
    op.drop_column('charging_session', 'average_power')
    op.drop_column('charging_session', 'peak_power')
    op.drop_column('charging_session', 'fuel_type')
    
    op.drop_column('charging_point', 'last_telemetry_update')
    op.drop_column('charging_point', 'current_flow')
    op.drop_column('charging_point', 'current_pressure')
    op.drop_column('charging_point', 'current_temperature')
    op.drop_column('charging_point', 'purity_level')
    op.drop_column('charging_point', 'temperature_range_max')
    op.drop_column('charging_point', 'temperature_range_min')
    op.drop_column('charging_point', 'flow_rate')
    op.drop_column('charging_point', 'dispensing_pressure')
    op.drop_column('charging_point', 'current')
    op.drop_column('charging_point', 'voltage')
    op.drop_column('charging_point', 'connector_type')
    op.drop_column('charging_point', 'fuel_type')
    
    op.drop_column('station', 'max_dispensing_pressure')
    op.drop_column('station', 'hydrogen_purity')
    op.drop_column('station', 'hydrogen_storage_capacity')
    op.drop_column('station', 'station_type')
    op.drop_column('station', 'fuel_types')
    
    # Rimuovere enum types
    op.execute('DROP TYPE IF EXISTS connectortype')
    op.execute('DROP TYPE IF EXISTS fueltype')