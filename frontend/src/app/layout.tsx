import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KUBE-AI Master Dashboard",
  description: "MLOps Control Plane",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      {/* This is where the magic happens. 
        We inject the dark mode directly into the DOM body.
      */}
      <body className="bg-neutral-950 text-neutral-100 antialiased">
        {children}
      </body>
    </html>
  );
}