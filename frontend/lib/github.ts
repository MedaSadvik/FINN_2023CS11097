import "server-only";

/** True when this deployment is allowed to start company builds. */
export const buildsEnabled = Boolean(process.env.BUILD_GITHUB_TOKEN);

/**
 * Ask GitHub to run the build-company workflow. The token can only start workflows on this one repository, and
 * lives in a server-only environment variable. The model key and the Supabase secret key are NOT here: they sit in
 * the repository's Actions secrets and only the job can read them.
 */
export async function dispatchBuild(ticker: string, requestId: number): Promise<boolean> {
  const token = process.env.BUILD_GITHUB_TOKEN;
  if (!token) return false;
  const repo = process.env.BUILD_GITHUB_REPO ?? "MedaSadvik/FINN_2023CS11097";
  const ref = process.env.BUILD_GITHUB_REF ?? "main";
  try {
    const res = await fetch(`https://api.github.com/repos/${repo}/actions/workflows/build-company.yml/dispatches`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ref, inputs: { ticker, request_id: String(requestId) } }),
      cache: "no-store",
    });
    return res.status === 204;
  } catch {
    return false;
  }
}
