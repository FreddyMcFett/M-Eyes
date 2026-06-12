"""TLS certificate store (server certs, CSRs, trusted CAs) for HTTPS

Revision ID: 0003_certificates
Revises: 0002_infoblox_features
Create Date: 2026-06-12

"""
import sqlalchemy as sa
from alembic import op

revision = '0003_certificates'
down_revision = '0002_infoblox_features'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'certificates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('kind', sa.String(length=16), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('subject', sa.String(length=512), nullable=False),
        sa.Column('issuer', sa.String(length=512), nullable=False),
        sa.Column('san', sa.JSON(), nullable=True),
        sa.Column('serial', sa.String(length=128), nullable=False),
        sa.Column('fingerprint_sha256', sa.String(length=128), nullable=False),
        sa.Column('key_type', sa.String(length=32), nullable=False),
        sa.Column('is_self_signed', sa.Boolean(), nullable=False),
        sa.Column('not_before', sa.DateTime(), nullable=True),
        sa.Column('not_after', sa.DateTime(), nullable=True),
        sa.Column('private_key_pem', sa.Text(), nullable=True),
        sa.Column('csr_pem', sa.Text(), nullable=True),
        sa.Column('cert_pem', sa.Text(), nullable=True),
        sa.Column('chain_pem', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_certificates_name'), 'certificates', ['name'], unique=False)
    op.create_index(op.f('ix_certificates_kind'), 'certificates', ['kind'], unique=False)
    op.create_index(op.f('ix_certificates_status'), 'certificates', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_certificates_status'), table_name='certificates')
    op.drop_index(op.f('ix_certificates_kind'), table_name='certificates')
    op.drop_index(op.f('ix_certificates_name'), table_name='certificates')
    op.drop_table('certificates')
