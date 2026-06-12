"""Next-gen DDI: zone roles (secondary/forward), RPZ threat feeds, API keys

Revision ID: 0004_nextgen_ddi
Revises: 0003_certificates
Create Date: 2026-06-12

"""
import sqlalchemy as sa
from alembic import op

revision = '0004_nextgen_ddi'
down_revision = '0003_certificates'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('zones', sa.Column('role', sa.String(length=16), nullable=False,
                                     server_default='primary'))
    op.add_column('zones', sa.Column('primaries', sa.String(length=512), nullable=False,
                                     server_default=''))

    op.create_table(
        'rpz_threat_feeds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('url', sa.String(length=512), nullable=False),
        sa.Column('action', sa.String(length=16), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('refresh_hours', sa.Integer(), nullable=False),
        sa.Column('last_synced', sa.DateTime(), nullable=True),
        sa.Column('last_status', sa.String(length=255), nullable=False),
        sa.Column('entry_count', sa.Integer(), nullable=False),
        sa.Column('domains', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_rpz_threat_feeds_name'), 'rpz_threat_feeds', ['name'], unique=True)

    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('prefix', sa.String(length=16), nullable=False),
        sa.Column('key_hash', sa.String(length=64), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_api_keys_name'), 'api_keys', ['name'], unique=True)
    op.create_index(op.f('ix_api_keys_key_hash'), 'api_keys', ['key_hash'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_api_keys_key_hash'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_name'), table_name='api_keys')
    op.drop_table('api_keys')
    op.drop_index(op.f('ix_rpz_threat_feeds_name'), table_name='rpz_threat_feeds')
    op.drop_table('rpz_threat_feeds')
    op.drop_column('zones', 'primaries')
    op.drop_column('zones', 'role')
