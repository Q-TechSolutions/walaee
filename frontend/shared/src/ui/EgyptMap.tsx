/**
 * خريطة مصر بالمتاجر المتعاقدة.
 *
 * ما تجيب عنه هذه الخريطة سؤال واحد: **هل تصلون إليّ؟** كل قرار
 * في تصميمها تابع لذلك السؤال.
 *
 * لماذا فقاعة لكل محافظة لا نقطة لكل فرع: أكثر من ثلث الفروع في
 * القاهرة الكبرى. رسمها نقاطًا يعطي بقعة سوداء فوق القاهرة وفراغًا
 * يوحي بأن لا شيء في الصعيد — والحقيقة عكس ذلك. الفقاعة تقول
 * العدد صراحةً، والنقاط الصغيرة تحتها تبقي التوزيع الحقيقي مرئيًا.
 *
 * ── إمكانية الوصول ──
 * الخريطة رسم، والرسم لا يُقرأ. لذلك تحتها جدول نصّي مخفي بصريًا
 * يحمل نفس الأرقام بالضبط. ليس «بديلًا مختصرًا»: من يتصفّح بقارئ
 * شاشة يحصل على المعلومة كاملة لا على اعتذار.
 *
 * الفقاعات أزرار حقيقية في شجرة إمكانية الوصول (`role="button"`
 * و`tabIndex`) وتستجيب للوحة المفاتيح — لأن الضغط عليها يغيّر
 * قائمة المتاجر المعروضة، فهو فعل لا زينة.
 */

import { useMemo, useState } from "react";

import {
  BORDER,
  LAKE_NASSER,
  NILE,
  NILE_DAMIETTA,
  NILE_ROSETTA,
  VIEW,
  bubbleCore,
  bubbleRadius,
  pathFrom,
  project,
} from "./egypt";
import type { PublicBranch, PublicGovernorate } from "../api/public";
import { t } from "../i18n/locale";

export interface EgyptMapProps {
  governorates: PublicGovernorate[];
  branches?: PublicBranch[];
  /** رمز المحافظة المحدّدة حاليًا — يتحكّم به المستضيف */
  selected?: string | null;
  onSelect?: (code: string | null) => void;
  /** يخفي النقاط الفردية — لخريطة مصغّرة داخل بطاقة */
  compact?: boolean;
  title?: string;
}

export function EgyptMap({
  governorates,
  branches = [],
  selected = null,
  onSelect,
  compact = false,
  title = t("خريطة المتاجر المتعاقدة في مصر"),
}: EgyptMapProps) {
  const [hovered, setHovered] = useState<string | null>(null);

  /**
   * المغطّاة مرتّبة تنازليًا بالعدد.
   *
   * الترتيب هنا ترتيب **رسم** لا عرض: العنصر المتأخر في SVG يُرسَم
   * فوق ما قبله ويلتقط النقر. فقاعات القاهرة والجيزة والقليوبية
   * متداخلة بحكم الجغرافيا، ورسم الأصغر أولًا كان يدفن أكبر رقم في
   * الخريطة كله تحت جاره — فيرى الزائر «١٤» في القاهرة الكبرى ولا
   * يرى «٢٤» إطلاقًا، ولا يستطيع الضغط عليها.
   *
   * الأكبر أولًا يجعل الصغيرة فوقها: كلها مرئية وكلها قابلة للنقر،
   * لأن الكبيرة تبقى مكشوفة فيما حول الصغيرة.
   */
  const covered = useMemo(
    () =>
      governorates
        .filter((item) => item.branch_count > 0)
        .sort((a, b) => b.branch_count - a.branch_count),
    [governorates],
  );
  const max = useMemo(
    () => covered.reduce((top, item) => Math.max(top, item.branch_count), 0),
    [covered],
  );

  const outline = useMemo(() => pathFrom(BORDER, true), []);
  const nile = useMemo(
    () => [NILE, NILE_ROSETTA, NILE_DAMIETTA].map((line) => pathFrom(line)),
    [],
  );
  const lake = useMemo(() => pathFrom(LAKE_NASSER), []);

  const dots = useMemo(
    () =>
      compact
        ? []
        : branches.map((branch) => ({
            ...project(branch.lat, branch.lng),
            key: branch.id,
            color: branch.color,
            governorate: branch.governorate,
          })),
    [branches, compact],
  );

  const active = hovered ?? selected;
  const activeItem = covered.find((item) => item.code === active) ?? null;

  function toggle(code: string) {
    onSelect?.(selected === code ? null : code);
  }

  return (
    <div className="eg-map">
      <svg
        viewBox={`0 0 ${VIEW.width} ${VIEW.height}`}
        className="eg-svg"
        role="img"
        aria-label={title}
        // الرسم كلّه مخفي عن القارئ الصوتي: الجدول أسفله هو
        // المصدر النصّي، وقراءة الاثنين تعني سماع كل رقم مرتين.
      >
        <defs>
          {/* تدرّج الصحراء: فاتح في الغرب حيث لا عمران، أدفأ قليلًا
              عند وادي النيل. يوحي بالمكان بلا أن يزاحم العلامات. */}
          <linearGradient id="eg-land" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--eg-land-1)" />
            <stop offset="100%" stopColor="var(--eg-land-2)" />
          </linearGradient>
          <filter id="eg-lift" x="-40%" y="-40%" width="180%" height="180%">
            <feDropShadow
              dx="0"
              dy="3"
              stdDeviation="5"
              floodColor="rgba(23,20,31,0.28)"
            />
          </filter>
        </defs>

        <path d={outline} className="eg-land" fill="url(#eg-land)" />

        <path d={lake} className="eg-water eg-lake" />
        {nile.map((line, index) => (
          <path key={index} d={line} className="eg-water" />
        ))}

        {/* النقاط الفردية أسفل الفقاعات: توزيع حقيقي بلا أن تسرق
            الانتباه من الأرقام */}
        {dots.map((dot) => (
          <circle
            key={dot.key}
            cx={dot.x}
            cy={dot.y}
            r={3.2}
            className={`eg-dot ${active && dot.governorate !== active ? "is-dim" : ""}`}
            style={{ fill: dot.color }}
          />
        ))}

        {covered.map((item) => {
          const { x, y } = project(item.lat, item.lng);
          const r = bubbleRadius(item.branch_count, max);
          const isActive = active === item.code;
          const isChosen = selected === item.code;

          return (
            <g
              key={item.code}
              className={[
                "eg-bubble",
                isActive && "is-active",
                isChosen && "is-selected",
                active && !isActive && "is-dim",
              ]
                .filter(Boolean)
                .join(" ")}
              role={onSelect ? "button" : undefined}
              tabIndex={onSelect ? 0 : undefined}
              aria-pressed={onSelect ? isChosen : undefined}
              aria-label={`${t(item.name)}: ${t("{n} فرع", { n: item.branch_count })}`}
              onMouseEnter={() => setHovered(item.code)}
              onMouseLeave={() => setHovered(null)}
              onFocus={() => setHovered(item.code)}
              onBlur={() => setHovered(null)}
              onClick={() => onSelect && toggle(item.code)}
              onKeyDown={(event) => {
                if (!onSelect) return;
                // المسافة تمرّر الصفحة افتراضيًا — تُمنع هنا لأن
                // العنصر يتصرّف كزر
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  toggle(item.code);
                }
              }}
            >
              <circle cx={x} cy={y} r={r} className="eg-bubble-halo" />
              <circle
                cx={x}
                cy={y}
                r={bubbleCore(r)}
                className="eg-bubble-core"
                filter={isActive ? "url(#eg-lift)" : undefined}
              />
            </g>
          );
        })}

        {/* ══ الأرقام في مسار ثانٍ فوق الدوائر كلها ══
            ترتيب الرسم يحلّ النقر ولا يحلّ القراءة: الأكبر يُرسَم
            أولًا فيغطّيه جاره الأصغر، فيختفي «٢٤» — أهم رقم في
            الخريطة — تحت «١٤». فصل الأرقام في طبقة أخيرة يجعلها
            كلها مقروءة مهما تداخلت الدوائر تحتها.

            `pointer-events: none` عليها في CSS، فلا تسرق نقرة من
            الدائرة التي تعلوها. */}
        {covered.map((item) => {
          const { x, y } = project(item.lat, item.lng);
          return (
            <text
              key={item.code}
              x={x}
              y={y}
              dy="0.36em"
              className={`eg-bubble-text ${active && active !== item.code ? "is-dim" : ""}`}
            >
              {item.branch_count}
            </text>
          );
        })}
      </svg>

      {/* بطاقة التفاصيل خارج الـSVG: النص داخل SVG لا يلتفّ ولا
          يرث أنماط الصفحة، والاسم العربي الطويل يخرج من الإطار. */}
      <div className={`eg-tip ${activeItem ? "is-on" : ""}`} aria-hidden="true">
        {activeItem && (
          <>
            <strong>{t(activeItem.name)}</strong>
            <span className="num">{activeItem.branch_count}</span> {t("فرع ·")}{" "}
            <span className="num">{activeItem.brand_count}</span> {t("متجر")}
          </>
        )}
      </div>

      <table className="sr-only">
        <caption>{title}</caption>
        <thead>
          <tr>
            <th scope="col">{t("المحافظة")}</th>
            <th scope="col">{t("عدد الفروع")}</th>
            <th scope="col">{t("عدد المتاجر")}</th>
          </tr>
        </thead>
        <tbody>
          {covered.map((item) => (
            <tr key={item.code}>
              <th scope="row">{t(item.name)}</th>
              <td>{item.branch_count}</td>
              <td>{item.brand_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
