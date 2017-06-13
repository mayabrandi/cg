"""change name of admin tables

Revision ID: 6c8c9701193d
Revises: aec83c9eb54d
Create Date: 2017-06-12 17:19:33.936212

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '6c8c9701193d'
down_revision = 'aec83c9eb54d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('admin_method',
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
    op.create_table('admin_customer',
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
    op.drop_table('admin.customer')
    op.drop_table('admin.method')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('admin.method',
    sa.Column('id', mysql.INTEGER(display_width=11), nullable=False),
    sa.Column('name', mysql.VARCHAR(length=128), nullable=False),
    sa.Column('document', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
    sa.Column('document_version', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
    sa.Column('description', mysql.TEXT(), nullable=False),
    sa.Column('limitations', mysql.TEXT(), nullable=True),
    sa.Column('last_updated', mysql.DATETIME(), nullable=True),
    sa.Column('comment', mysql.TEXT(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    mysql_default_charset='latin1',
    mysql_engine='InnoDB'
    )
    op.create_table('admin.customer',
    sa.Column('id', mysql.INTEGER(display_width=11), nullable=False),
    sa.Column('customer_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True),
    sa.Column('agreement_date', sa.DATE(), nullable=True),
    sa.Column('agreement_registration', mysql.VARCHAR(length=32), nullable=True),
    sa.Column('scout_access', mysql.TINYINT(display_width=1), autoincrement=False, nullable=True),
    sa.Column('primary_contact_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True),
    sa.Column('delivery_contact_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True),
    sa.Column('uppmax_account', mysql.VARCHAR(length=32), nullable=True),
    sa.Column('project_account_ki', mysql.VARCHAR(length=32), nullable=True),
    sa.Column('project_account_kth', mysql.VARCHAR(length=32), nullable=True),
    sa.Column('organisation_number', mysql.VARCHAR(length=32), nullable=True),
    sa.Column('invoice_address', mysql.TEXT(), nullable=True),
    sa.Column('invoice_reference', mysql.VARCHAR(length=32), nullable=True),
    sa.Column('invoice_contact_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['customer_id'], ['customer.id'], name='admin.customer_ibfk_1'),
    sa.ForeignKeyConstraint(['delivery_contact_id'], ['user.id'], name='admin.customer_ibfk_2'),
    sa.ForeignKeyConstraint(['invoice_contact_id'], ['user.id'], name='admin.customer_ibfk_3'),
    sa.ForeignKeyConstraint(['primary_contact_id'], ['user.id'], name='admin.customer_ibfk_4'),
    sa.PrimaryKeyConstraint('id'),
    mysql_default_charset='latin1',
    mysql_engine='InnoDB'
    )
    op.drop_table('admin_customer')
    op.drop_table('admin_method')
    # ### end Alembic commands ###
