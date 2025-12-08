import type { Metadata } from "next";
import "../styles.css";

export const metadata: Metadata = {
  title: "Fact-Check Assistant",
  description: "Verify Antisemitism-Related Claims",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
