/* Session-bound CSRF transport for browser forms, fetch and jQuery writes. */
(function () {
  var originalFetch = window.fetch.bind(window);
  var tokenPromise = null;

  function getToken() {
    if (!tokenPromise) {
      tokenPromise = originalFetch(docroot + '/csrf', { credentials: 'same-origin', cache: 'no-store' })
        .then(function (response) {
          if (!response.ok) throw new Error('csrf-bootstrap-failed');
          return response.json();
        })
        .then(function (data) {
          var token = data && data.csrf_token;
          if (typeof token !== 'string' || token.length < 40) throw new Error('csrf-bootstrap-failed');
          document.querySelectorAll('input[name="csrf_token"]').forEach(function (input) { input.value = token; });
          return token;
        })
        .catch(function (error) { tokenPromise = null; throw error; });
    }
    return tokenPromise;
  }

  function reportExpired(response) {
    if (response.status === 403 && response.headers.get('X-CSRF-Error') === '1' && window.alertify) {
      window.alertify.error('安全令牌无效或已过期，请刷新页面后重试。');
    }
    return response;
  }

  window.sfCsrf = { getToken: getToken };
  window.fetch = function (input, init) {
    init = init || {};
    var method = String(init.method || (input && input.method) || 'GET').toUpperCase();
    if (method !== 'POST') return originalFetch(input, init);
    return getToken().then(function (token) {
      var headers = new Headers(init.headers || (input && input.headers) || {});
      headers.set('X-CSRF-Token', token);
      return originalFetch(input, Object.assign({}, init, { headers: headers, credentials: init.credentials || 'same-origin' }));
    }).then(reportExpired);
  };

  if (window.jQuery) {
    var originalAjax = window.jQuery.ajax;
    window.jQuery.ajax = function (url, options) {
      var settings = typeof url === 'object' ? url : Object.assign({}, options || {}, { url: url });
      var method = String(settings.method || settings.type || 'GET').toUpperCase();
      if (method !== 'POST') return originalAjax.apply(this, arguments);
      var deferred = window.jQuery.Deferred();
      getToken().then(function (token) {
        var beforeSend = settings.beforeSend;
        settings.beforeSend = function (xhr) {
          xhr.setRequestHeader('X-CSRF-Token', token);
          return beforeSend ? beforeSend.apply(this, arguments) : undefined;
        };
        originalAjax(settings).done(function () { deferred.resolveWith(this, arguments); })
          .fail(function (xhr) {
            if (xhr && xhr.status === 403 && xhr.getResponseHeader('X-CSRF-Error') === '1' && window.alertify) {
              window.alertify.error('安全令牌无效或已过期，请刷新页面后重试。');
            }
            deferred.rejectWith(this, arguments);
          });
      }).catch(function () {
        deferred.rejectWith(null, [{ status: 0, responseText: 'CSRF token unavailable' }, 'error', 'CSRF token unavailable']);
      });
      return deferred.promise();
    };
  }

  document.addEventListener('submit', function (event) {
    var form = event.target;
    if (!(form instanceof HTMLFormElement) || String(form.method).toUpperCase() !== 'POST' || form.dataset.csrfReady === '1') return;
    event.preventDefault();
    getToken().then(function (token) {
      var field = form.querySelector('input[name="csrf_token"]');
      if (!field) {
        field = document.createElement('input');
        field.type = 'hidden';
        field.name = 'csrf_token';
        form.appendChild(field);
      }
      field.value = token;
      form.dataset.csrfReady = '1';
      if (form.requestSubmit) form.requestSubmit(event.submitter);
      else form.submit();
    }).catch(function () {
      if (window.alertify) window.alertify.error('无法验证安全令牌，请刷新页面后重试。');
    });
  }, true);

  document.addEventListener('DOMContentLoaded', function () { getToken().catch(function () {}); });
})();
