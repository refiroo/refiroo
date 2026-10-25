/**
 * The application's mark: the refiroo mascot and, beside it, the name as the wordmark. `refiroo` is
 * the name of the application; the engine inside it is the RDM engine. A model whose `product.name`
 * is its own (an organisation's name for its deployment, the instance's name of 0.12 D338) shows that name
 * next to the mark; the default names show the mark alone. The images are in `public/brand`.
 */

const DEFAULT_PRODUCT_NAMES = ["refiroo", "rdm engine"];

export function isDefaultProductName(name: string): boolean {
  return DEFAULT_PRODUCT_NAMES.includes(name.trim().toLowerCase());
}

export function ProductMark({ name }: { name: string }) {
  return (
    <span className="brand-mark">
      <img className="brand-mascot" src="/brand/refiroo-mascot.png" alt="" width={32} height={32} />
      <img className="brand-wordmark" src="/brand/refiroo-wordmark.png" alt="refiroo" height={18} />
      {!isDefaultProductName(name) && <strong className="brand-instance">{name}</strong>}
    </span>
  );
}

/** The mascot alone, larger, for a screen that has nothing else to show (loading, nothing to open). */
export function BrandMascot({ size = 72 }: { size?: number }) {
  return <img className="brand-mascot-large" src="/brand/refiroo-mascot.png" alt="" width={size} height={size} />;
}
