"""Add the external_links table

Revision ID: e3edd86918fd
Revises: 66e36d0a2853
Create Date: 2019-06-26 14:43:51.915267

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3edd86918fd'
down_revision = '66e36d0a2853'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('external_links',
    sa.Column('external_link_id', 
              sa.BigInteger().with_variant(sa.Integer, 'sqlite'), 
              nullable=False),
    sa.Column('wordform_id', sa.BigInteger(), nullable=True),
    sa.Column('source_name', sa.String(length=5), nullable=True),
    sa.Column('source_id', sa.String(length=10), nullable=True),
    sa.ForeignKeyConstraint(['wordform_id'], ['wordforms.wordform_id'], ),
    sa.PrimaryKeyConstraint('external_link_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('external_links')
    # ### end Alembic commands ###
