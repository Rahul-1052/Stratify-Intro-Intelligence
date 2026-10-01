import type { Metadata } from 'next';
import './globals.css';
import './memory.css';
export const metadata: Metadata = { title: 'Stratify — Creator intelligence', description: 'Understand your content through evidence.' };
export default function Layout({children}: {children: React.ReactNode}) {
  return <html lang="en"><body>{children}</body></html>;
}
