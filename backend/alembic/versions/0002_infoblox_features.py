"""DNS views, DNS firewall (RPZ), extensible attributes, DNSSEC flag, discovery

Revision ID: 0002_infoblox_features
Revises: 0001_initial
Create Date: 2026-06-12

"""
from alembic import op
import sqlalchemy as sa


revision = '0002_infoblox_features'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('dns_views',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('match_clients', sa.String(length=512), nullable=False),
    sa.Column('description', sa.String(length=255), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dns_views_name'), 'dns_views', ['name'], unique=True)

    op.create_table('rpz_rules',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('fqdn', sa.String(length=255), nullable=False),
    sa.Column('action', sa.String(length=16), nullable=False),
    sa.Column('substitute', sa.String(length=255), nullable=False),
    sa.Column('comment', sa.String(length=255), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rpz_rules_fqdn'), 'rpz_rules', ['fqdn'], unique=True)

    op.create_table('extattr_defs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('type', sa.String(length=16), nullable=False),
    sa.Column('comment', sa.String(length=255), nullable=False),
    sa.Column('allowed_values', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_extattr_defs_name'), 'extattr_defs', ['name'], unique=True)

    op.create_table('extattr_values',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('def_id', sa.Integer(), nullable=False),
    sa.Column('object_type', sa.String(length=32), nullable=False),
    sa.Column('object_id', sa.Integer(), nullable=False),
    sa.Column('value', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['def_id'], ['extattr_defs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('def_id', 'object_type', 'object_id', name='uq_extattr_object')
    )
    op.create_index(op.f('ix_extattr_values_object_id'), 'extattr_values', ['object_id'],
                    unique=False)
    op.create_index(op.f('ix_extattr_values_object_type'), 'extattr_values', ['object_type'],
                    unique=False)

    with op.batch_alter_table('zones') as batch:
        batch.add_column(sa.Column('view_id', sa.Integer(), nullable=True))
        batch.add_column(sa.Column('dnssec_enabled', sa.Boolean(), nullable=False,
                                   server_default=sa.false()))
        batch.create_foreign_key('fk_zones_view_id', 'dns_views', ['view_id'], ['id'],
                                 ondelete='SET NULL')
        batch.create_unique_constraint('uq_zone_name_view', ['name', 'view_id'])
    # zone names are no longer globally unique: the same zone may exist in several views
    op.drop_index(op.f('ix_zones_name'), table_name='zones')
    op.create_index(op.f('ix_zones_name'), 'zones', ['name'], unique=False)

    with op.batch_alter_table('ip_addresses') as batch:
        batch.add_column(sa.Column('last_seen', sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('ip_addresses') as batch:
        batch.drop_column('last_seen')

    op.drop_index(op.f('ix_zones_name'), table_name='zones')
    op.create_index(op.f('ix_zones_name'), 'zones', ['name'], unique=True)
    with op.batch_alter_table('zones') as batch:
        batch.drop_constraint('uq_zone_name_view', type_='unique')
        batch.drop_constraint('fk_zones_view_id', type_='foreignkey')
        batch.drop_column('dnssec_enabled')
        batch.drop_column('view_id')

    op.drop_index(op.f('ix_extattr_values_object_type'), table_name='extattr_values')
    op.drop_index(op.f('ix_extattr_values_object_id'), table_name='extattr_values')
    op.drop_table('extattr_values')
    op.drop_index(op.f('ix_extattr_defs_name'), table_name='extattr_defs')
    op.drop_table('extattr_defs')
    op.drop_index(op.f('ix_rpz_rules_fqdn'), table_name='rpz_rules')
    op.drop_table('rpz_rules')
    op.drop_index(op.f('ix_dns_views_name'), table_name='dns_views')
    op.drop_table('dns_views')
