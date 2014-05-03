class Post(object):
    exists = os.path.exists
    getmtime = os.path.getmtime

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
        return self.full_path[:-4] + '.html'

    @property
    def is_html_fresh(self):
        if not self.exists(self.html_path):
            return False
        rst_time = self.getmtime(self.full_path)
        html_time = self.getmtime(self.html_path)
        if rst_time > html_time:
            return False
        return True

    def refresh_html(self, force=False):
        if not force:
            if self.is_html_fresh:
                return False

        with codecs.open(self.full_path, 'r', 'utf-8') as rst:
            md = markdown.Markdown(extensions=self.MARKDOWN_EXTS)
            source = rst.read()
            html = md.convert(source)

            if 'title' in md.Meta:
                title = ' '.join(md.Meta['title'])
                self.title = title

            with codecs.open(self.html_path, 'w', 'utf-8') as f:
                f.write(html)

        return True

    def push(self, force):
        if not self.blogid or not self.postid:
            raise ConfigError('Post %s not published yet' % self.name)

        self.refresh_html(force)

        remote = self.config.remote()
        rpost = remote.get_post(self.blogid, self.postid)
        rpost.title = self.title
        rpost.labels = self.labels
        rpost.updated = datetime.now()

        with codecs.open(self.html_path, 'r', 'utf-8') as html:
            rpost.content = html.read()

        remote.update(rpost)


class TestPost(unittest.TestCase):
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
