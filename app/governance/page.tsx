import { redirect } from "next/navigation";

/** The Governance panel is the admin console at /admin (app/admin/page.tsx:
 *  audit log, pending approvals, integrity badge). This alias resolves the
 *  intuitive /governance URL — matching the sidebar "Governance" label — to it,
 *  so a typed or bookmarked /governance no longer hard-404s. The sidebar button
 *  routes to /admin directly (lib/nav.ts), which renders the same panel. */
export default function GovernancePage() {
  redirect("/admin");
}
