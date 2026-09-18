/* ===================================================================
   Project page interactions
   -------------------------------------------------------------------
   Videos are pre-composed side-by-side (baseline | ours) by
   prepare_assets.py, so the two halves are always frame-synchronised
   and a single <video> element is enough.
   =================================================================== */

(function () {
  'use strict';

  var DATA = window.PAGE_DATA;

  var PLAY_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>';

  /* ------------------------------------------------------------ Player */

  function Player(root, options) {
    this.root = root;
    this.scenes = options.scenes;
    this.methods = options.methods;
    this.methodId = options.methodId;
    this.sceneIndex = 0;
    this.showLabels = options.showLabels !== false;

    if (!this.scenes.length) {
      this.root.innerHTML = placeholderMarkup();
      return;
    }

    this.build();
    this.selectScene(0);
  }

  Player.prototype.build = function () {
    var stage = el('div', 'player__stage');

    this.video = el('video');
    this.video.muted = true;
    this.video.loop = true;
    this.video.playsInline = true;
    this.video.setAttribute('playsinline', '');
    this.video.preload = 'metadata';

    this.split = el('div', 'player__split');

    this.overlay = el('button', 'player__overlay');
    this.overlay.type = 'button';
    this.overlay.innerHTML = PLAY_ICON;
    this.overlay.setAttribute('aria-label', 'Play or pause');

    stage.append(this.video, this.split, this.overlay);
    this.root.append(stage);

    if (this.showLabels) {
      this.labels = el('div', 'player__labels');
      this.leftLabel = el('span');
      this.rightLabel = el('span');
      this.rightLabel.textContent = DATA.oursLabel;
      this.labels.append(this.leftLabel, this.rightLabel);
      this.root.append(this.labels);
    }

    this.thumbs = el('div', 'thumbs');
    this.root.append(this.thumbs);

    var self = this;
    this.scenes.forEach(function (scene, i) {
      var btn = el('button', 'thumb');
      btn.type = 'button';
      btn.setAttribute('aria-pressed', 'false');
      btn.setAttribute('aria-label', 'Scene ' + scene.id);

      var img = el('img');
      img.src = scene.thumb;
      img.alt = '';
      img.loading = 'lazy';
      btn.append(img);

      btn.addEventListener('click', function () { self.selectScene(i); });
      self.thumbs.append(btn);
    });

    this.overlay.addEventListener('click', function () { self.toggle(); });
    this.video.addEventListener('play', function () { self.syncOverlay(); });
    this.video.addEventListener('pause', function () { self.syncOverlay(); });
    this.video.addEventListener('error', function () { self.showMissing(); });
  };

  Player.prototype.currentScene = function () {
    return this.scenes[this.sceneIndex];
  };

  Player.prototype.selectScene = function (index) {
    this.sceneIndex = index;

    var buttons = this.thumbs.querySelectorAll('.thumb');
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].setAttribute('aria-pressed', String(i === index));
    }

    this.load(0);
  };

  Player.prototype.setMethod = function (methodId) {
    if (methodId === this.methodId) return;
    this.methodId = methodId;
    this.load(this.video.currentTime || 0);
  };

  Player.prototype.load = function (startAt) {
    var src = this.currentScene().videos[this.methodId];

    if (this.leftLabel) {
      this.leftLabel.textContent = labelOf(this.methods, this.methodId);
    }

    if (!src) {
      this.showMissing();
      return;
    }

    this.clearMissing();

    var self = this;
    var resume = function () {
      if (startAt > 0 && startAt < self.video.duration) {
        self.video.currentTime = startAt;
      }
      self.video.play().catch(function () { self.syncOverlay(); });
      self.video.removeEventListener('loadedmetadata', resume);
    };

    this.video.addEventListener('loadedmetadata', resume);
    this.video.src = src;
    this.video.load();
  };

  Player.prototype.toggle = function () {
    if (this.video.paused) {
      this.video.play().catch(function () {});
    } else {
      this.video.pause();
    }
  };

  Player.prototype.syncOverlay = function () {
    this.overlay.dataset.visible = this.video.paused ? 'true' : 'false';
  };

  Player.prototype.showMissing = function () {
    if (this.missing) return;
    this.missing = el('div', 'placeholder placeholder--overlay');
    this.missing.innerHTML =
      'Video not available for this combination.<br>' +
      'Run <code>python prepare_assets.py</code> to generate the web assets.';
    this.root.querySelector('.player__stage').append(this.missing);
  };

  Player.prototype.clearMissing = function () {
    if (this.missing) {
      this.missing.remove();
      this.missing = null;
    }
  };

  /* ----------------------------------------------------------- Helpers */

  function el(tag, className) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    return node;
  }

  function labelOf(methods, id) {
    for (var i = 0; i < methods.length; i++) {
      if (methods[i].id === id) return methods[i].label;
    }
    return id;
  }

  function placeholderMarkup() {
    return '<div class="placeholder">No videos configured yet.<br>' +
      'Run <code>python prepare_assets.py</code> to generate ' +
      '<code>static/js/data.js</code> and the web-ready clips.</div>';
  }

  /* -------------------------------------------------------------- Init */

  function init() {
    if (!DATA) return;

    var teaserRoot = document.getElementById('teaser-player');
    if (teaserRoot) {
      new Player(teaserRoot, {
        scenes: DATA.scenes.filter(function (s) { return s.videos[DATA.teaserMethod]; }),
        methods: DATA.methods,
        methodId: DATA.teaserMethod,
        showLabels: true
      });
    }

    var resultsRoot = document.getElementById('results-player');
    var optionsRoot = document.getElementById('method-options');

    if (resultsRoot && optionsRoot) {
      var player = new Player(resultsRoot, {
        scenes: DATA.scenes,
        methods: DATA.methods,
        methodId: DATA.methods[0].id,
        showLabels: true
      });

      DATA.methods.forEach(function (method, i) {
        var btn = el('button', 'method-btn');
        btn.type = 'button';
        btn.textContent = method.label;
        btn.setAttribute('aria-pressed', String(i === 0));

        btn.addEventListener('click', function () {
          optionsRoot.querySelectorAll('.method-btn').forEach(function (b) {
            b.setAttribute('aria-pressed', 'false');
          });
          btn.setAttribute('aria-pressed', 'true');
          player.setMethod(method.id);
        });

        optionsRoot.append(btn);
      });
    }

    var copyBtn = document.getElementById('copy-bibtex');
    if (copyBtn) {
      copyBtn.addEventListener('click', function () {
        var text = document.getElementById('bibtex-content').textContent;
        navigator.clipboard.writeText(text).then(function () {
          copyBtn.textContent = 'Copied';
          setTimeout(function () { copyBtn.textContent = 'Copy'; }, 1600);
        });
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
