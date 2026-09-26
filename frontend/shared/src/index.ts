/** نقطة التصدير الوحيدة للمكتبة المشتركة. */

export { api, request, configureApi, WalaeeApiError } from "./api/client";
export {
  readTokens,
  writeTokens,
  clearTokens,
  isAuthenticated,
  decodeAccess,
  namespacedKey,
} from "./api/tokens";
export * from "./api/types";
export {
  fetchNetwork,
  forgetNetwork,
  byReach,
  branchesOf,
} from "./api/public";
export type {
  PublicNetwork,
  PublicBrand,
  PublicBranch,
  PublicGovernorate,
  NetworkStats,
} from "./api/public";

export * as fmt from "./utils/format";
export { appPath, basePath, hardRedirect, isAt } from "./utils/navigation";

export {
  Badge,
  Button,
  Card,
  Empty,
  ErrorBox,
  Field,
  Loading,
  Modal,
  PageHeader,
  Ring,
  Skeleton,
  Spinner,
  Stat,
} from "./ui/components";
export { DemoAccountsPanel, useDemoAccounts } from "./ui/DemoAccounts";
export { Icon, categoryIcon, CATEGORY_ICONS, PROGRAM_ICONS } from "./ui/icons";
export type { IconName } from "./ui/icons";
export { Logo, LogoMark } from "./ui/Logo";
export { AuthLayout, AuthPoint } from "./ui/AuthLayout";
export { EgyptMap } from "./ui/EgyptMap";
export { project, pathFrom, BOUNDS, VIEW } from "./ui/egypt";
export type { DemoCustomer, DemoStaff } from "./ui/DemoAccounts";
export {
  useAction,
  useApi,
  useCountdown,
  useDebounced,
  useInterval,
} from "./ui/hooks";

export {
  t,
  pick,
  getLocale,
  setLocale,
  localeLabel,
  applyDocument,
  LOCALES,
} from "./i18n/locale";
export type { Locale } from "./i18n/locale";
export { EN } from "./i18n/en";
export {
  getTheme,
  setTheme,
  resolvedTheme,
  applyTheme,
  THEMES,
} from "./ui/theme";
export type { Theme } from "./ui/theme";
export {
  useLocale,
  useTheme,
  applyPreferences,
  ThemeToggle,
  LocaleToggle,
  PreferenceBar,
  LocaleBoundary,
} from "./ui/Preferences";
