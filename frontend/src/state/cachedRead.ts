/**
 * A read made once and kept for the page load: the one mechanism for what changes only by signing
 * in again or by a new release of the engine (the signed-in person, the system's static parts).
 * Everyone who asks shares the one request. A failed read is not kept, so the next ask retries;
 * `forget` drops the answer, which is what a Retry does. Anything that can change while the page
 * is open (the system's activation, capabilities, permissions) is not read through here.
 */
export function cachedRead<T>(read: () => Promise<T>) {
  let pending: Promise<T> | undefined;
  return {
    get(): Promise<T> {
      if (!pending) {
        const own: Promise<T> = Promise.resolve()
          .then(read)
          .catch((cause: unknown) => {
            if (pending === own) pending = undefined;
            throw cause;
          });
        pending = own;
      }
      return pending;
    },
    forget() {
      pending = undefined;
    },
  };
}
