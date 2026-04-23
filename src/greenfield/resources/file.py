from dataclasses import field
from os import chmod, chown
from typing import Literal, Unpack, TypedDict, NotRequired
from pathlib import Path
from pwd import getpwnam, getpwuid
from grp import getgrgid, getgrnam

from jinja2 import Environment, FileSystemLoader

from greenfield.resources import Resource
from greenfield.state import StateDiff, CheckResult, Ok, Drift, Error


class FileArgs(TypedDict):
    state: NotRequired[Literal['absent', 'present', 'directory']]
    template: NotRequired[str]
    content: NotRequired[str]
    mode: NotRequired[str]
    owner: NotRequired[str]
    group: NotRequired[str]


class File(Resource[FileArgs]):
    def __init__(self, name: str, /, **kwargs: Unpack[FileArgs]):
        super().__init__(name, **kwargs)
        self.path = Path(name)
        if self.config.get('state') == 'directory' and (self.config.get('content') or self.config.get('template')):
            raise Exception('Conflicting settings: directory and content')

    def check(self) -> CheckResult:
        """Check if file exists, can be created, matches desired state, etc"""
        diffs: list[StateDiff] = []
        state = self.config.get('state', 'present')
        match state:
            case 'present':
                if not self.path.exists():
                    diffs.append(StateDiff(
                        field='exists',
                        expected=True,
                        actual=False,
                    ))

                    if (template := self.config.get('template')):
                        expected_content = self._render_template(template)
                        diffs.append(StateDiff(
                            field='content',
                            expected=expected_content,
                            actual='',
                        ))
                    elif (expected_content := self.config.get('content')):
                        diffs.append(StateDiff(
                            field='content',
                            expected=expected_content,
                            actual='',
                        ))

                    # mode
                    if (mode := self.config.get('mode')):
                        diffs.append(StateDiff(
                            field='mode',
                            expected=mode,
                            actual='',
                        ))
                    # owner
                    if (owner := self.config.get('owner')):
                        diffs.append(StateDiff(
                            field='owner',
                            expected=owner,
                            actual='',
                        ))
                    # group
                    if (group := self.config.get('group')):
                        diffs.append(StateDiff(
                            field='group',
                            expected=group,
                            actual='',
                        ))

                    return Drift(diffs=diffs)
            case 'absent':
                if self.path.exists():
                    diffs.append(StateDiff(
                        field='exists',
                        expected=False,
                        actual=True
                    ))
            case 'directory':
                if not self.path.exists():
                    diffs.append(StateDiff(
                        field='exists',
                        expected=True,
                        actual=False,
                    ))
                elif not self.path.is_dir():
                    return Error(
                        message=f'Expected path {self.path} as directory',
                    )

        try:
            if 'template' in self.config:
                expected = self._render_template(self.config['template'])
                actual = self.path.read_text()

                if expected != actual:
                    diffs.append(StateDiff(
                        field='content',
                        expected=expected,
                        actual=actual
                    ))

            if 'content' in self.config:
                actual_content = self.path.read_text()
                expected_content = self.config['content']
                if expected_content != actual_content:
                    diffs.append(StateDiff(
                        field='content',
                        expected=expected_content,
                        actual=actual_content,
                    ))

            if 'mode' in self.config:
                actual_mode = oct(self.path.stat().st_mode)[-4:]
                expected_mode = self.config['mode']

                if actual_mode != expected_mode:
                    diffs.append(StateDiff(
                        field='mode',
                        expected=expected_mode,
                        actual=actual_mode,
                    ))

            if 'owner' in self.config:
                actual_owner = getpwuid(self.path.stat().st_uid).pw_name
                expected_owner = self.config['owner']

                if actual_owner != expected_owner:
                    diffs.append(StateDiff(
                        field='owner',
                        expected=expected_owner,
                        actual=actual_owner,
                    ))

            if 'group' in self.config:
                actual_group = getgrgid(self.path.stat().st_gid).gr_name
                expected_group = self.config['group']

                if actual_group != expected_group:
                    diffs.append(StateDiff(
                        field='group',
                        expected=expected_group,
                        actual=actual_group,
                    ))

        except Exception as e:
            return Error(message='Failed to check file state', exception=e)

        if diffs:
            return Drift(diffs=diffs)
        return Ok()

    def apply(self):
        """Create/update the file"""
        state = self.config.get('state', 'present')

        if state == 'absent':
            if self.path.exists():
                if self.path.is_dir():
                    self.path.rmdir()
                else: # file
                    self.path.unlink()
            return

        # check if it's a file and a dir is requested or vice versa
        # delete and recreate below
        if self.path.exists():
            is_dir = self.path.is_dir()
            expected_is_dir = (state == 'directory')

            if is_dir != expected_is_dir:
                if is_dir:
                    self.path.rmdir()
                else:
                    self.path.unlink()

        # Create parent dirs
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if state == 'directory':
            self.path.mkdir(exist_ok=True)
        else: # we're a file request
            # content
            if (template := self.config.get('template')):
                content = self._render_template(template)
                self.path.write_text(content)
            elif (content := self.config.get('content')):
                self.path.write_text(content)
            else:
                self.path.touch()

        if 'mode' in self.config:
            mode_int = int(self.config['mode'], 8)
            chmod(self.path, mode_int)


        # defaults - if they're -1, they will remain unchanged
        uid, gid = (-1, -1)

        # check mode
        if 'owner' in self.config:
            uid = getpwnam(self.config['owner']).pw_uid

        if 'group' in self.config:
            gid = getgrnam(self.config['group']).gr_gid

        if uid != -1 or gid != -1:
            chown(self.path, uid, gid)


    def _render_template(self, template_name: str) -> str:
        # just a stub for now
        # TODO: make this some sort of system config path
        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template(template_name)

        context = {}
        if (self.bundle is not None) and (bundle_instance := self.bundle()):
            if bundle_instance is not None:
                context.update(bundle_instance.locals)

        # TODO: capture locals of bundle and insert somehow
        context.update(self.config)

        return template.render(**context)
