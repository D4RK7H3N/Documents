import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type ReportFilters } from "./client";

export const keys = {
  me: ["me"] as const,
  projects: ["projects"] as const,
  reports: ["reports"] as const,
  report: (id: number) => ["reports", id] as const,
  stats: ["stats"] as const,
  settings: ["settings"] as const,
};

export const useMe = () => useQuery({ queryKey: keys.me, queryFn: api.auth.me, retry: false });
export const useProjects = () => useQuery({ queryKey: keys.projects, queryFn: api.projects.list });
export const useStats = () => useQuery({ queryKey: keys.stats, queryFn: api.stats });
export const useSettings = () => useQuery({ queryKey: keys.settings, queryFn: api.settings });

export const useReports = (filters: ReportFilters, refetchInterval: number | false) =>
  useQuery({
    queryKey: [...keys.reports, filters],
    queryFn: () => api.reports.list(filters),
    refetchInterval,
  });

export const useReport = (id: number) =>
  useQuery({ queryKey: keys.report(id), queryFn: () => api.reports.get(id) });

export function useReportAction(action: "requeue" | "reject" | "approvePr") {
  const client = useQueryClient();
  return useMutation<unknown, Error, number>({
    mutationFn: (id: number) => api.reports[action](id),
    onSuccess: (_data, id) => {
      client.invalidateQueries({ queryKey: keys.report(id) });
      client.invalidateQueries({ queryKey: keys.reports });
      client.invalidateQueries({ queryKey: keys.stats });
    },
  });
}

export function useProjectMutations() {
  const client = useQueryClient();
  const invalidate = () => client.invalidateQueries({ queryKey: keys.projects });
  return {
    create: useMutation({ mutationFn: api.projects.create, onSuccess: invalidate }),
    update: useMutation({
      mutationFn: ({ id, data }: { id: number; data: Parameters<typeof api.projects.update>[1] }) =>
        api.projects.update(id, data),
      onSuccess: invalidate,
    }),
    remove: useMutation({ mutationFn: api.projects.remove, onSuccess: invalidate }),
    rotate: useMutation({ mutationFn: api.projects.rotateKey, onSuccess: invalidate }),
  };
}
