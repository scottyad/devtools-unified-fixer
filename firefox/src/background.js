// One background worker serializes identity creation across all DevTools panels.
let trialIdentityPromise;
function getTrialIdentity() {
  if (!trialIdentityPromise) {
    trialIdentityPromise = assistantBrowser.storage.local.get('devtools_trial_key').then(async stored => {
      if (stored.devtools_trial_key) return stored.devtools_trial_key;
      const key = 'FREE-' + crypto.randomUUID().toUpperCase();
      await assistantBrowser.storage.local.set({devtools_trial_key: key});
      return key;
    }).catch(err => { trialIdentityPromise = null; throw err; });
  }
  return trialIdentityPromise;
}
assistantBrowser.runtime.onMessage.addListener((message, sender, respond) => {
  if (message.type !== 'getTrialIdentity') return;
  getTrialIdentity().then(key => respond({key}), err => respond({error: err.message}));
  return true;
});
