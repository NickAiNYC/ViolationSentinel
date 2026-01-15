"""Initial database schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2024-01-15 17:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create organizations table
    op.create_table('organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('subscription_tier', sa.Enum('FREE', 'PRO', 'ENTERPRISE', name='subscriptiontier'), nullable=False),
        sa.Column('subscription_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('subscription_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('billing_email', sa.String(length=255), nullable=True),
        sa.Column('stripe_customer_id', sa.String(length=100), nullable=True),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
        sa.UniqueConstraint('stripe_customer_id')
    )
    op.create_index(op.f('ix_organizations_name'), 'organizations', ['name'], unique=False)
    op.create_index(op.f('ix_organizations_slug'), 'organizations', ['slug'], unique=False)
    
    # Create properties table
    op.create_table('properties',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bbl', sa.String(length=10), nullable=False),
        sa.Column('bin', sa.String(length=7), nullable=True),
        sa.Column('address_line1', sa.String(length=255), nullable=False),
        sa.Column('address_line2', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=2), nullable=False),
        sa.Column('zip_code', sa.String(length=10), nullable=False),
        sa.Column('borough', sa.String(length=50), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('property_type', sa.String(length=50), nullable=True),
        sa.Column('units_count', sa.Integer(), nullable=True),
        sa.Column('year_built', sa.Integer(), nullable=True),
        sa.Column('square_footage', sa.Integer(), nullable=True),
        sa.Column('portfolio_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('latitude >= -90 AND latitude <= 90', name='check_latitude_range'),
        sa.CheckConstraint('longitude >= -180 AND longitude <= 180', name='check_longitude_range'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('bbl')
    )
    op.create_index(op.f('ix_properties_bbl'), 'properties', ['bbl'], unique=False)
    op.create_index(op.f('ix_properties_bin'), 'properties', ['bin'], unique=False)
    op.create_index(op.f('ix_properties_borough'), 'properties', ['borough'], unique=False)
    op.create_index('ix_properties_location', 'properties', ['latitude', 'longitude'], unique=False)
    op.create_index('ix_properties_org_borough', 'properties', ['organization_id', 'borough'], unique=False)
    op.create_index(op.f('ix_properties_organization_id'), 'properties', ['organization_id'], unique=False)
    op.create_index(op.f('ix_properties_portfolio_id'), 'properties', ['portfolio_id'], unique=False)
    op.create_index(op.f('ix_properties_property_type'), 'properties', ['property_type'], unique=False)


def downgrade() -> None:
    op.drop_table('properties')
    op.drop_table('organizations')
    op.execute('DROP TYPE subscriptiontier')
