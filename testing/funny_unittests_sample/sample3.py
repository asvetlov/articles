class FileSystem(object):
    class Impl(object):
        exists = os.path.exists
        getmtime = os.path.getmtime
        open = codecs.open

    _impl = Impl()

    def __init__(self, config):
        self._config = config

    def open(fname, mode):
        return self._impl.open(fname, mode, 'utf-8')

    def exists(self, fname):
        return self._impl.exists(fname)

    def getmtime(self, fname):
        return self._impl.getmtime(fname)

    def full_name(self, rel_name):
        return os.path.join(self._config.root, rel_name)

    def replace_ext(self, fname, new_ext):
        root, old_ext = os.path.splitext(fname)
        return root + new_ext


class Post(object):
    MARKDOWN_EXTS = ('codehighlight', 'meta')

    def __init__(self, config, name, rst_file,
                 title=None, slug=None, labels=None,
                 blogid=None
                 postid=None):
        self.config = config
        self.name = name
        self.rst_file = rst_file
        self.title = title
        self.slug = slug
        self.blogid = blogid
        self.postid = postid
        self.labels = frozenset(labels) if labels else frozenset()

    @property
    def full_path(self):
        f = self.rst_file
        return os.path.join(self.config.root, f)

    @property
    def html_path(self):
        return self.config.file_system.replace_ext(self.full_path, '.html')

    @property
    def is_html_fresh(self):
        fs = self.config.file_system
        if not fs.exists(self.html_path):
            return False
        rst_time = fs.getmtime(self.full_path)
        html_time = fs.getmtime(self.html_path)
        if rst_time > html_time:
            return False
        return True

    def refresh_html(self, force=False):
        fs = self.config.file_system
        if not force:
            if self.is_html_fresh:
                return False

        with fs.open(self.full_path, 'r') as rst:
            md = markdown.Markdown(extensions=self.MARKDOWN_EXTS)
            source = rst.read()
            html = md.convert(source)

            if 'title' in md.Meta:
                title = ' '.join(md.Meta['title'])
                self.title = title

            with fs.open(self.html_path, 'w') as f:
                f.write(html)

        return True


class TestPost(unittest.TestCase):
    def setUp(self):
        self.mocker = mocker
        self.config = Config('root')
        self.fs = self.mocker.mock()
        self.config.file_system._impl = self.fs
        self.post = Post(self.config, 'name', 'file.rst')

    def test_is_html_fresh_yes(self):
        with self.mocker.order():
            self.fs.exists('root/file.rst')
            self.mocker.result(True)
            self.fs.getmtime('root/file.rst')
            self.mocker.result(5)
            self.fs.getmtime('root/file.html')
            self.mocker.result(10)

        with self.mocker:
            self.assertEqual(True, self.post.is_html_fresh)

    def test_ctor(self):
        cfg = object()
        post = Post(cfg, 'name', 'file.rst', 'Title', 'slug', ['label1'],
                    'blogid', 'postid')
        self.assertEqual(cfg, post.config)
        self.assertEqual('name', post.name)
        self.assertEqual('file.rst', post.file)
        self.assertEqual('Title', post.title)
        self.assertEqual('slug', post.slug)
        self.assertEqual(frozenset(['label1']), post.labels)
        self.assertEqual('blogid', post.blogid)
        self.assertEqual('postid', post.postid)

    def test_full_path(self):
        class Config(object):
            root = 'config-root'
        cfg = Config()
        post = Post(cfg, 'name', 'file.rst')

        self.assertEqual('config-root/file.rst', post.full_path)

    def test_is_html_fresh_not_found(self):
        mocker = mocker.Mocker()

        exists = mocker.mock()
        config = mocker.mock()

        with mocker.order():
            exists('root/file.html')
            mocker.result(False)
            config.root
            mocker.result('root')

        with mocker:
            post = Post(config, 'file.rst')
            post.exists = exists

            self.assertEqual(False, post.is_html_fresh)

    def test_is_html_fresh_yes(self):
        mocker = mocker.Mocker()

        exists = mocker.mock()
        config = mocker.mock()
        getmtime = mocker.mock()

        with mocker.order():
            exists('root/file.html')
            mocker.result(True)
            config.root
            mocker.result('root')
            getmtime('root/file.rst')
            mocker.result(5)
            getmtime('root/file.html')
            mocker.result(10)

        with mocker:
            post = Post(config, 'file.rst')
            post.exists = exists

            self.assertEqual(True, post.is_html_fresh)

    def test_is_html_fresh_not(self):
        mocker = mocker.Mocker()

        exists = mocker.mock()
        config = mocker.mock()
        getmtime = mocker.mock()

        with mocker.order():
            exists('root/file.html')
            mocker.result(True)
            config.root
            mocker.result('root')
            getmtime('root/file.rst')
            mocker.result(10)
            getmtime('root/file.html')
            mocker.result(5)

        with mocker:
            post = Post(config, 'file.rst')
            post.exists = exists

            self.assertEqual(False, post.is_html_fresh)
