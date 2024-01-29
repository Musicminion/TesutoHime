"""add user groups

Revision ID: cd4339e8dce3
Revises: 6d235526cd40
Create Date: 2024-01-29 15:53:27.985094

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd4339e8dce3'
down_revision: Union[str, None] = '6d235526cd40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('course_tag',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('site_owner', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('term',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('course',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), server_default='', nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=True),
        sa.Column('term_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tag_id'], ['course_tag.id'], ),
        sa.ForeignKeyConstraint(['term_id'], ['term.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_course_tag_id'), 'course', ['tag_id'], unique=False)
    op.create_index(op.f('ix_course_term_id'), 'course', ['term_id'], unique=False)
    op.create_table('enrollment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('admin', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['course.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_enrollment_course_id'), 'enrollment', ['course_id'], unique=False)
    op.create_index(op.f('ix_enrollment_user_id'), 'enrollment', ['user_id'], unique=False)
    op.create_index('ix_enrollment_user_id_course_id', 'enrollment', ['user_id', 'course_id'], unique=True)
    op.create_table('group',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), server_default='', nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['course.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_group_course_id'), 'group', ['course_id'], unique=False)
    op.create_table('contest_group',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('contest_id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['contest_id'], ['contest.id'], ),
        sa.ForeignKeyConstraint(['group_id'], ['group.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contest_group_contest_id'), 'contest_group', ['contest_id'], unique=False)
    op.create_index(op.f('ix_contest_group_group_id'), 'contest_group', ['group_id'], unique=False)
    op.create_table('group_realname_reference',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('realname_reference_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['group.id'], ),
        sa.ForeignKeyConstraint(['realname_reference_id'], ['realname_reference.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_group_realname_reference_group_id'), 'group_realname_reference', ['group_id'], unique=False)
    op.create_index('ix_group_realname_reference_group_id_realname_reference_id', 'group_realname_reference', ['group_id', 'realname_reference_id'], unique=True)
    op.create_index(op.f('ix_group_realname_reference_realname_reference_id'), 'group_realname_reference', ['realname_reference_id'], unique=False)
    op.create_table('problem_privilege',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('problem_id', sa.Integer(), nullable=False),
        sa.Column('privilege', sa.Enum('readonly', 'owner', name='problemprivilegetype'), nullable=False),
        sa.Column('comment', sa.Text(), server_default='', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['problem_id'], ['problem.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_problem_privilege_problem_id'), 'problem_privilege', ['problem_id'], unique=False)
    op.create_index(op.f('ix_problem_privilege_user_id'), 'problem_privilege', ['user_id'], unique=False)

    op.add_column('problem', sa.Column('course_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_problem_course_id'), 'problem', ['course_id'], unique=False)
    op.create_foreign_key(None, 'problem', 'course', ['course_id'], ['id'])
    op.add_column('realname_reference', sa.Column('course_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_realname_reference_course_id'), 'realname_reference', ['course_id'], unique=False)
    op.create_index('ix_realname_reference_student_id_course_id', 'realname_reference', ['student_id', 'course_id'], unique=True)
    op.create_foreign_key(None, 'realname_reference', 'course', ['course_id'], ['id'])

    op.execute("INSERT INTO course (name) VALUES ('acmoj');")
    op.execute("UPDATE problem SET course_id = (SELECT id FROM course);")
    op.execute("UPDATE realname_reference SET course_id = (SELECT id FROM course);")

    op.alter_column('problem', 'course_id', nullable=False)
    op.alter_column('realname_reference', 'course_id', nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('realname_reference_course_id_fkey', 'realname_reference', type_='foreignkey')
    op.drop_index('ix_realname_reference_student_id_course_id', table_name='realname_reference')
    op.drop_index(op.f('ix_realname_reference_course_id'), table_name='realname_reference')
    op.drop_column('realname_reference', 'course_id')
    op.drop_constraint('problem_course_id_fkey', 'problem', type_='foreignkey')
    op.drop_index(op.f('ix_problem_course_id'), table_name='problem')
    op.drop_column('problem', 'course_id')
    op.drop_index(op.f('ix_problem_privilege_user_id'), table_name='problem_privilege')
    op.drop_index(op.f('ix_problem_privilege_problem_id'), table_name='problem_privilege')
    op.drop_table('problem_privilege')
    op.drop_index(op.f('ix_group_realname_reference_realname_reference_id'), table_name='group_realname_reference')
    op.drop_index('ix_group_realname_reference_group_id_realname_reference_id', table_name='group_realname_reference')
    op.drop_index(op.f('ix_group_realname_reference_group_id'), table_name='group_realname_reference')
    op.drop_table('group_realname_reference')
    op.drop_index(op.f('ix_contest_group_group_id'), table_name='contest_group')
    op.drop_index(op.f('ix_contest_group_contest_id'), table_name='contest_group')
    op.drop_table('contest_group')
    op.drop_index(op.f('ix_group_course_id'), table_name='group')
    op.drop_table('group')
    op.drop_index('ix_enrollment_user_id_course_id', table_name='enrollment')
    op.drop_index(op.f('ix_enrollment_user_id'), table_name='enrollment')
    op.drop_index(op.f('ix_enrollment_course_id'), table_name='enrollment')
    op.drop_table('enrollment')
    op.drop_index(op.f('ix_course_term_id'), table_name='course')
    op.drop_index(op.f('ix_course_tag_id'), table_name='course')
    op.drop_table('course')
    op.drop_table('term')
    op.drop_table('course_tag')

    op.execute('DROP TYPE problemprivilegetype;')
    # ### end Alembic commands ###
