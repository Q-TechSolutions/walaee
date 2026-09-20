-- ══════════════════════════════════════════════════════════
--  حماية السجلات append-only على مستوى قاعدة البيانات.
--
--  الحارس في بايثون (apps.common.models.AppendOnlyModel) يمنع الخطأ
--  البرمجي العرضي. هذا الملف يمنع ما لا يستطيع بايثون منعه: تحديثًا
--  مباشرًا من psql أو من أداة إدارة أو من سكربت هجرة.
--
--  يُطبَّق يدويًا بعد أول migrate:
--      psql -U walaee -d walaee -f infra/postgres/02-append-only.sql
--  (ليس ضمن docker-entrypoint-initdb.d لأن الجداول لا تكون موجودة بعد)
--
--  ⚠ لا يُطبَّق على قاعدة تطوير تُستخدم فيها `seed_demo --reset`،
--    لأن إعادة التهيئة تحذف القيود عمدًا وستصطدم بالحارس.
-- ══════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION walaee_forbid_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION
        'الجدول % بنمط append-only — التصحيح بقيد عكسي لا بتعديل أو حذف',
        TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS ledger_entry_immutable ON ledger_ledgerentry;
CREATE TRIGGER ledger_entry_immutable
    BEFORE UPDATE OR DELETE ON ledger_ledgerentry
    FOR EACH ROW EXECUTE FUNCTION walaee_forbid_mutation();

DROP TRIGGER IF EXISTS audit_log_immutable ON audit_auditlog;
CREATE TRIGGER audit_log_immutable
    BEFORE UPDATE OR DELETE ON audit_auditlog
    FOR EACH ROW EXECUTE FUNCTION walaee_forbid_mutation();
