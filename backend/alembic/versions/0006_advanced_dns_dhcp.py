"""Advanced DNS zone and DHCP scope configuration

Adds per-zone access-control / forwarding options and per-scope lease timing,
network-boot (PXE) and client-classification fields so operators can configure
the DNS and DHCP services to the depth expected of an enterprise DDI platform.

Revision ID: 0006_advanced_dns_dhcp
Revises: 0005_enterprise
Create Date: 2026-06-15

"""
import sqlalchemy as sa
from alembic import op

revision = '0006_advanced_dns_dhcp'
down_revision = '0005_enterprise'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Per-zone advanced DNS options ------------------------------------- #
    op.add_column('zones', sa.Column('allow_query', sa.String(length=512), nullable=False, server_default=''))
    op.add_column('zones', sa.Column('allow_transfer', sa.String(length=512), nullable=False, server_default=''))
    op.add_column('zones', sa.Column('allow_update', sa.String(length=512), nullable=False, server_default=''))
    op.add_column('zones', sa.Column('also_notify', sa.String(length=512), nullable=False, server_default=''))
    op.add_column('zones', sa.Column('forward_first', sa.Boolean(), nullable=False, server_default=sa.false()))

    # --- Per-scope advanced DHCP options ----------------------------------- #
    op.add_column('dhcp_subnets', sa.Column('valid_lifetime', sa.Integer(), nullable=True))
    op.add_column('dhcp_subnets', sa.Column('max_valid_lifetime', sa.Integer(), nullable=True))
    op.add_column('dhcp_subnets', sa.Column('renew_timer', sa.Integer(), nullable=True))
    op.add_column('dhcp_subnets', sa.Column('rebind_timer', sa.Integer(), nullable=True))
    op.add_column('dhcp_subnets', sa.Column('next_server', sa.String(length=64), nullable=True))
    op.add_column('dhcp_subnets', sa.Column('boot_file_name', sa.String(length=255), nullable=True))
    op.add_column('dhcp_subnets', sa.Column('client_class', sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column('dhcp_subnets', 'client_class')
    op.drop_column('dhcp_subnets', 'boot_file_name')
    op.drop_column('dhcp_subnets', 'next_server')
    op.drop_column('dhcp_subnets', 'rebind_timer')
    op.drop_column('dhcp_subnets', 'renew_timer')
    op.drop_column('dhcp_subnets', 'max_valid_lifetime')
    op.drop_column('dhcp_subnets', 'valid_lifetime')

    op.drop_column('zones', 'forward_first')
    op.drop_column('zones', 'also_notify')
    op.drop_column('zones', 'allow_update')
    op.drop_column('zones', 'allow_transfer')
    op.drop_column('zones', 'allow_query')
