"""add admin tables: customer + method

Revision ID: aec83c9eb54d
Revises: c7e06157fd9a
Create Date: 2017-06-12 17:16:05.430402

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aec83c9eb54d'
down_revision = 'c7e06157fd9a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('admin.method',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('document', sa.Integer(), nullable=False),
    sa.Column('document_version', sa.Integer(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('limitations', sa.Text(), nullable=True),
    sa.Column('last_updated', sa.DateTime(), nullable=True),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('admin.customer',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('customer_id', sa.Integer(), nullable=True),
    sa.Column('agreement_date', sa.Date(), nullable=True),
    sa.Column('agreement_registration', sa.String(length=32), nullable=True),
    sa.Column('scout_access', sa.Boolean(), nullable=True),
    sa.Column('primary_contact_id', sa.Integer(), nullable=True),
    sa.Column('delivery_contact_id', sa.Integer(), nullable=True),
    sa.Column('uppmax_account', sa.String(length=32), nullable=True),
    sa.Column('project_account_ki', sa.String(length=32), nullable=True),
    sa.Column('project_account_kth', sa.String(length=32), nullable=True),
    sa.Column('organisation_number', sa.String(length=32), nullable=True),
    sa.Column('invoice_address', sa.Text(), nullable=True),
    sa.Column('invoice_reference', sa.String(length=32), nullable=True),
    sa.Column('invoice_contact_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['customer_id'], ['customer.id'], ),
    sa.ForeignKeyConstraint(['delivery_contact_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['invoice_contact_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['primary_contact_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('admin.customer')
    op.drop_table('admin.method')
    # ### end Alembic commands ###