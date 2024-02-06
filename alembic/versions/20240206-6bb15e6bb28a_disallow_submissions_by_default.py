"""disallow submissions by default

Revision ID: 6bb15e6bb28a
Revises: 971d49f56617
Create Date: 2024-02-06 10:20:14.726929

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6bb15e6bb28a'
down_revision: Union[str, None] = '971d49f56617'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('problem', 'languages_accepted', server_default=sa.text("'{}'"))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('problem', 'languages_accepted', server_default=None)
    # ### end Alembic commands ###
