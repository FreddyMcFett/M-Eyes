"""Enterprise: SSO/RBAC user fields, asset management, integrations, automation

Revision ID: 0005_enterprise
Revises: 0004_nextgen_ddi
Create Date: 2026-06-13

"""
import sqlalchemy as sa
from alembic import op

revision = '0005_enterprise'
down_revision = '0004_nextgen_ddi'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- RBAC / SSO fields on the existing users table ---------------------- #
    op.add_column('users', sa.Column('email', sa.String(length=255), nullable=False, server_default=''))
    op.add_column('users', sa.Column('display_name', sa.String(length=128), nullable=False, server_default=''))
    op.add_column('users', sa.Column('auth_source', sa.String(length=16), nullable=False, server_default='local'))
    op.add_column('users', sa.Column('external_id', sa.String(length=255), nullable=False, server_default=''))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(), nullable=True))

    # --- SAML SSO configuration (single row) ------------------------------- #
    op.create_table(
        'sso_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('button_label', sa.String(length=64), nullable=False, server_default='Sign in with SSO'),
        sa.Column('idp_entity_id', sa.String(length=512), nullable=False, server_default=''),
        sa.Column('idp_sso_url', sa.String(length=512), nullable=False, server_default=''),
        sa.Column('idp_slo_url', sa.String(length=512), nullable=False, server_default=''),
        sa.Column('idp_x509_cert', sa.Text(), nullable=False, server_default=''),
        sa.Column('sp_entity_id', sa.String(length=512), nullable=False, server_default=''),
        sa.Column('base_url', sa.String(length=512), nullable=False, server_default=''),
        sa.Column('attr_username', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('attr_email', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('attr_display_name', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('attr_groups', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('role_mappings', sa.JSON(), nullable=True),
        sa.Column('default_role', sa.String(length=32), nullable=False, server_default='viewer'),
        sa.Column('allow_jit_provisioning', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('name_id_format', sa.String(length=128), nullable=False,
                  server_default='urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress'),
        sa.Column('sign_authn_requests', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('want_assertions_signed', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('want_response_signed', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('force_authn', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('allowed_clock_skew_seconds', sa.Integer(), nullable=False, server_default='120'),
        sa.Column('signature_algorithm', sa.String(length=128), nullable=False,
                  server_default='http://www.w3.org/2001/04/xmldsig-more#rsa-sha256'),
        sa.Column('sp_private_key', sa.Text(), nullable=False, server_default=''),
        sa.Column('sp_x509_cert', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- Asset management -------------------------------------------------- #
    op.create_table(
        'assets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('asset_type', sa.String(length=32), nullable=False, server_default='server'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='in_service'),
        sa.Column('criticality', sa.String(length=16), nullable=False, server_default='medium'),
        sa.Column('owner', sa.String(length=128), nullable=False, server_default=''),
        sa.Column('location', sa.String(length=128), nullable=False, server_default=''),
        sa.Column('department', sa.String(length=128), nullable=False, server_default=''),
        sa.Column('vendor', sa.String(length=128), nullable=False, server_default=''),
        sa.Column('model', sa.String(length=128), nullable=False, server_default=''),
        sa.Column('serial_number', sa.String(length=128), nullable=False, server_default=''),
        sa.Column('operating_system', sa.String(length=128), nullable=False, server_default=''),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('source', sa.String(length=64), nullable=False, server_default='manual'),
        sa.Column('external_id', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('last_seen', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_assets_name'), 'assets', ['name'], unique=False)
    op.create_index(op.f('ix_assets_external_id'), 'assets', ['external_id'], unique=False)

    op.create_table(
        'asset_interfaces',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False, server_default=''),
        sa.Column('mac', sa.String(length=32), nullable=False, server_default=''),
        sa.Column('ip', sa.String(length=64), nullable=False, server_default=''),
        sa.Column('hostname', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('ip_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ip_id'], ['ip_addresses.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_asset_interfaces_mac'), 'asset_interfaces', ['mac'], unique=False)
    op.create_index(op.f('ix_asset_interfaces_ip'), 'asset_interfaces', ['ip'], unique=False)

    op.create_table(
        'asset_tags',
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('asset_id', 'tag_id'),
    )

    # --- Integrations ------------------------------------------------------ #
    op.create_table(
        'integrations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('kind', sa.String(length=48), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('base_url', sa.String(length=512), nullable=False, server_default=''),
        sa.Column('username', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('secret', sa.Text(), nullable=False, server_default=''),
        sa.Column('verify_tls', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('last_status', sa.String(length=32), nullable=False, server_default='never'),
        sa.Column('last_message', sa.String(length=512), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_integrations_name'), 'integrations', ['name'], unique=True)
    op.create_index(op.f('ix_integrations_kind'), 'integrations', ['kind'], unique=False)

    # --- Automation -------------------------------------------------------- #
    op.create_table(
        'automation_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('kind', sa.String(length=48), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('interval_seconds', sa.Integer(), nullable=False, server_default='3600'),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('next_run_at', sa.DateTime(), nullable=True),
        sa.Column('last_status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('last_message', sa.String(length=512), nullable=False, server_default=''),
        sa.Column('run_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_automation_rules_name'), 'automation_rules', ['name'], unique=True)
    op.create_index(op.f('ix_automation_rules_kind'), 'automation_rules', ['kind'], unique=False)
    op.create_index(op.f('ix_automation_rules_next_run_at'), 'automation_rules', ['next_run_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_automation_rules_next_run_at'), table_name='automation_rules')
    op.drop_index(op.f('ix_automation_rules_kind'), table_name='automation_rules')
    op.drop_index(op.f('ix_automation_rules_name'), table_name='automation_rules')
    op.drop_table('automation_rules')

    op.drop_index(op.f('ix_integrations_kind'), table_name='integrations')
    op.drop_index(op.f('ix_integrations_name'), table_name='integrations')
    op.drop_table('integrations')

    op.drop_table('asset_tags')
    op.drop_index(op.f('ix_asset_interfaces_ip'), table_name='asset_interfaces')
    op.drop_index(op.f('ix_asset_interfaces_mac'), table_name='asset_interfaces')
    op.drop_table('asset_interfaces')
    op.drop_index(op.f('ix_assets_external_id'), table_name='assets')
    op.drop_index(op.f('ix_assets_name'), table_name='assets')
    op.drop_table('assets')

    op.drop_table('sso_config')

    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'external_id')
    op.drop_column('users', 'auth_source')
    op.drop_column('users', 'display_name')
    op.drop_column('users', 'email')
