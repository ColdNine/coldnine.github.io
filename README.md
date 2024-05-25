# [Github Pages *with Jekyll*](https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll/creating-a-github-pages-site-with-jekyll)

## Prerequisites
- Install Git
```shell
$ sudo apt-get install git
$ git --version
```
- Install Ruby
```shell
$ sudo apt-get install ruby-full
$ ruby -v
```
- Install Jekyll & Bundler
```shell
$ sudo apt-get install ruby-full build-essential zlib1g-dev

$ echo '# Install Ruby Gems to ~/gems' >> ~/.bashrc
$ echo 'export GEM_HOME="$HOME/gems"' >> ~/.bashrc
$ echo 'export PATH="$HOME/gems/bin:$PATH"' >> ~/.bashrc
$ source ~/.bashrc

$ gem install jekyll bundler
```

## Create GitHub Pages
### Creating Repository
1) New Repository
2) Owner/Repository name: `user`/`<user>.github.io`

### Creating Site
```shell
$ git clone https://github.com/user/user.github.io.git
$ cd user.github.io
$ mkdir user && cd user
$ jekyll new --skip-bundle .
$ vi .gitignore
Gemfile.lock
$ vi Gemfile
#gem "jekyll", "~> 4.3.3"
# correct version Jekyll will be installed as a dependency of the github-pages gem
# replace 'GITHUB-PAGES-VERSION' with github-pages version in https://pages.github.com/versions
gem "github-pages", "~> GITHUB-PAGES-VERSION", group: :jekyll_plugins
# Jekyll serve fails on Ruby 3.0: https://github.com/jekyll/jekyll/issues/8523
gem "webrick"
$ bundle install
$ mv * .gitignore .. && rm -rf user

# local test
$ bundle exec jekyll serve

# git push
$ git add .
$ git commit -m 'Initial GitHub pages site with Jekyll'
$ git remote add origin https://github.com/user/user.github.io.git
$ git push -u origin BRANCH

# open site "https://user.github.io.git"
```

### Changing Themes
```shell
$ cd $HOME_DIR
$ vi _config.yml
#theme: minima
remote_theme: jekyll/minima
plugins:
  - jekyll-feed
  - jekyll-remote-theme

minima:
  skin: dark
```

### Changing Branches
1. Github
2. Repository(Github Pages)
3. Settings
4. Code and automation
5. Pages: `Deploy from a branch` + `BRANCH` `FOLDER` + **Save** (*may take some time*)

## Reference
- [Jekyll](https://jekyllrb.com)
- [Jekyll on Ubuntu](https://jekyllrb.com/docs/installation/ubuntu)
- [Supported Themes](https://pages.github.com/themes)
- [Remote Themes](http://jekyllthemes.org)