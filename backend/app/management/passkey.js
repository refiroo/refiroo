/*
 * The engine's one script (Product 0.12 I4c, D390): it asks the browser for a passkey, creating one
 * or using one, and posts the browser's answer to the engine. Everything else on the engine's pages
 * is plain HTML. The pages allow this file alone (script-src 'self'), nothing inline and nothing
 * from another site, and load it only where a passkey is offered. A button names what it does:
 *
 *   data-passkey="register"  the Add a passkey page; data-return is where it goes afterwards
 *   data-passkey="login"     the sign-in page, a passkey alone; the form's hidden fields are the
 *                            browser's authorization request
 *   data-passkey="second"    the second step after a password; data-step is the step's token
 *
 * The engine verifies everything; this file decides nothing.
 */
(function () {
  "use strict";

  var REQUEST = [
    "response_type",
    "client_id",
    "redirect_uri",
    "code_challenge",
    "code_challenge_method",
    "state",
  ];

  function toBytes(text) {
    var base64 = text.replace(/-/g, "+").replace(/_/g, "/");
    while (base64.length % 4) base64 += "=";
    var raw = atob(base64);
    var bytes = new Uint8Array(raw.length);
    for (var i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
    return bytes.buffer;
  }

  function toText(buffer) {
    var bytes = new Uint8Array(buffer);
    var raw = "";
    for (var i = 0; i < bytes.length; i++) raw += String.fromCharCode(bytes[i]);
    return btoa(raw).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  function post(path, body) {
    return fetch(path, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(function (response) {
      return response
        .json()
        .catch(function () {
          return {};
        })
        .then(function (data) {
          return { ok: response.ok, data: data };
        });
    });
  }

  function say(message) {
    var note = document.getElementById("passkey-note");
    if (!note) return;
    note.textContent = message;
    note.hidden = !message;
  }

  function refused(answer) {
    var error = new Error((answer.data && answer.data.error) || "The engine refused the passkey.");
    error.engine = true;
    return error;
  }

  function describe(error) {
    if (error && error.engine) return error.message;
    if (error && error.name === "NotAllowedError")
      return "The passkey was cancelled or took too long. Try again.";
    if (error && error.name === "InvalidStateError")
      return "This device already has a passkey for you here.";
    return "This browser could not use a passkey here. Try again, or sign in another way.";
  }

  function request() {
    var fields = {};
    REQUEST.forEach(function (name) {
      var input = document.querySelector('form input[type="hidden"][name="' + name + '"]');
      if (input) fields[name] = input.value;
    });
    return fields;
  }

  function created(credential) {
    var response = credential.response;
    return {
      id: credential.id,
      rawId: toText(credential.rawId),
      type: credential.type,
      authenticatorAttachment: credential.authenticatorAttachment || null,
      clientExtensionResults: credential.getClientExtensionResults(),
      response: {
        clientDataJSON: toText(response.clientDataJSON),
        attestationObject: toText(response.attestationObject),
        transports: response.getTransports ? response.getTransports() : [],
      },
    };
  }

  function asserted(credential) {
    var response = credential.response;
    return {
      id: credential.id,
      rawId: toText(credential.rawId),
      type: credential.type,
      authenticatorAttachment: credential.authenticatorAttachment || null,
      clientExtensionResults: credential.getClientExtensionResults(),
      response: {
        clientDataJSON: toText(response.clientDataJSON),
        authenticatorData: toText(response.authenticatorData),
        signature: toText(response.signature),
        userHandle: response.userHandle ? toText(response.userHandle) : null,
      },
    };
  }

  function register(button) {
    var name = document.getElementById("passkey-name");
    return post("/oauth/passkeys/registration/options", {}).then(function (started) {
      if (!started.ok) throw refused(started);
      var options = started.data.options;
      options.challenge = toBytes(options.challenge);
      options.user.id = toBytes(options.user.id);
      (options.excludeCredentials || []).forEach(function (item) {
        item.id = toBytes(item.id);
      });
      return navigator.credentials.create({ publicKey: options }).then(function (credential) {
        return post("/oauth/passkeys/registration/verify", {
          ceremony: started.data.ceremony,
          credential: created(credential),
          name: name ? name.value : null,
        }).then(function (done) {
          if (!done.ok) throw refused(done);
          window.location.assign(button.getAttribute("data-return") || "/");
        });
      });
    });
  }

  function authenticate(button, mode) {
    var body = mode === "second" ? { step: button.getAttribute("data-step") } : request();
    return post("/oauth/passkeys/authentication/options", body).then(function (started) {
      if (!started.ok) throw refused(started);
      var options = started.data.options;
      options.challenge = toBytes(options.challenge);
      (options.allowCredentials || []).forEach(function (item) {
        item.id = toBytes(item.id);
      });
      return navigator.credentials.get({ publicKey: options }).then(function (credential) {
        return post("/oauth/passkeys/authentication/verify", {
          ceremony: started.data.ceremony,
          credential: asserted(credential),
        }).then(function (done) {
          if (!done.ok) throw refused(done);
          window.location.assign(done.data.redirect);
        });
      });
    });
  }

  document.addEventListener("click", function (event) {
    var target = event.target;
    var button = target && target.closest ? target.closest("[data-passkey]") : null;
    if (!button || button.disabled) return;
    event.preventDefault();
    if (!window.PublicKeyCredential || !navigator.credentials) {
      say("This browser does not support passkeys. Sign in another way.");
      return;
    }
    var mode = button.getAttribute("data-passkey");
    say("");
    button.disabled = true;
    var work = mode === "register" ? register(button) : authenticate(button, mode);
    work.catch(function (error) {
      button.disabled = false;
      say(describe(error));
    });
  });
})();
