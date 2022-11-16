import argparse
import os
import shutil


IGNORE_FILE_NAME = '.syncignore'


class Operation:
    MOVE = "MOVE"
    ADD = "ADD"
    DEL = "DEL"

    def __init__(self, type_, *values):
        self.type_ = type_
        self.values = values

    def __repr__(self):
        if self.type_ == self.MOVE:
            return f'{self.type_}: {self.values[0]} -> {self.values[1]}'
        return f'{self.type_}: {self.values[0]}'


class Files:
    def __init__(self, root):
        self.root = root
        self.files = {}

    def _build_path(self, path, parent=False):
        s = f'{self.root}/{path}'
        if parent:
            s = '/'.join(s.split('/')[:-1])
        return s

    def search(self):
        self.files = {}
        self._search()

    def _search(self, path=''):
        full_path = self._build_path(path)
        file_name = full_path.split('/')[-1]
        if os.path.isfile(full_path):
            stats = os.stat(full_path)
            key = (
                file_name,
                int(os.stat(full_path).st_mtime),
                stats.st_size
            )
            if key in self.files:
                print(full_path)
                raise Exception()
            self.files[key] = path
            return

        file_list = os.listdir(full_path)
        ignore_files = {IGNORE_FILE_NAME}
        if IGNORE_FILE_NAME in file_list:
            with open(f'{full_path}/{IGNORE_FILE_NAME}') as f:
                ignore_files |= {line.strip() for line in f}

        for p in file_list:
            if p not in ignore_files:
                self._search(p if path == '' else f'{path}/{p}')

    def compare(self, other):
        ret = {}
        for key, value in other.files.items():
            if key not in self.files:
                ret[key] = Operation(Operation.DEL, other.files[key])

        for key, value in self.files.items():
            if key in other.files:
                if self.files[key] != other.files[key]:
                    ret[key] = Operation(
                        Operation.MOVE,
                        other.files[key],
                        self.files[key]
                    )
            else:
                ret[key] = Operation(Operation.ADD, self.files[key])

        return ret

    def sync(self, other):
        for key, operation in self.compare(other).items():
            if operation.type_ == Operation.ADD:
                os.makedirs(
                    other._build_path(self.files[key], parent=True),
                    exist_ok=True
                )
                shutil.copy2(
                    self._build_path(self.files[key]),
                    other._build_path(self.files[key]),
                )
            elif operation.type_ == Operation.DEL:
                os.remove(other._build_path(other.files[key]))
            else:
                os.makedirs(
                    other._build_path(self.files[key], parent=True),
                    exist_ok=True
                )
                shutil.move(
                    other._build_path(other.files[key]),
                    other._build_path(self.files[key]),
                )

    def clean(self, path=''):
        full_path = self._build_path(path)
        if os.path.isfile(full_path):
            return True

        flag = False

        for p in os.listdir(full_path):
            is_exist = self.clean(p if path == '' else f'{path}/{p}')
            flag = True if not flag and is_exist else flag

        if not flag:
            os.rmdir(full_path)
        return flag


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('src', type=str)
    parser.add_argument('dest', type=str)
    parser.add_argument('-d', '--dry_run', action='store_true')
    args = parser.parse_args()

    src = Files(args.src)
    dest = Files(args.dest)

    src.search()
    dest.search()

    if args.dry_run:
        for key, value in src.compare(dest).items():
            print(value)
    else:
        src.sync(dest)
        dest.clean()
