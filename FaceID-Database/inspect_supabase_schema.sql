-- ==============================================================================
-- Truy vấn READ-ONLY xuất cấu trúc schema hiện tại trên Supabase (JSON)
-- Cách dùng:
--   1. Mở Supabase Dashboard -> SQL Editor -> New query.
--   2. Dán toàn bộ nội dung file này và bấm Run.
--   3. Copy giá trị ô kết quả `supabase_schema_snapshot` và ghi đè vào file:
--      FaceID-Database/supabase_schema_snapshot.json
-- Lưu ý: Chỉ đọc metadata (bảng, cột, constraint, index, RLS, view, RPC),
--        KHÔNG đọc dữ liệu thật và KHÔNG chứa mật khẩu/secret.
-- ==============================================================================

SELECT jsonb_pretty(jsonb_build_object(
  'exported_at', now(),
  'extensions', (
    SELECT COALESCE(jsonb_agg(extname ORDER BY extname), '[]'::jsonb)
    FROM pg_extension
  ),
  'tables', (
    SELECT COALESCE(jsonb_object_agg(t.table_name, jsonb_build_object(
      'rls_enabled', pt.rowsecurity,
      'columns', (
        SELECT COALESCE(jsonb_agg(jsonb_build_object(
          'name', c.column_name,
          'type', c.udt_name,
          'nullable', c.is_nullable,
          'default', c.column_default
        ) ORDER BY c.ordinal_position), '[]'::jsonb)
        FROM information_schema.columns c
        WHERE c.table_schema = 'public' AND c.table_name = t.table_name
      ),
      'constraints', (
        SELECT COALESCE(jsonb_agg(jsonb_build_object(
          'name', con.conname,
          'type', con.contype,
          'definition', pg_get_constraintdef(con.oid)
        ) ORDER BY con.conname), '[]'::jsonb)
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
        WHERE nsp.nspname = 'public' AND rel.relname = t.table_name
      ),
      'indexes', (
        SELECT COALESCE(jsonb_agg(jsonb_build_object(
          'name', idx.indexname,
          'definition', idx.indexdef
        ) ORDER BY idx.indexname), '[]'::jsonb)
        FROM pg_indexes idx
        WHERE idx.schemaname = 'public' AND idx.tablename = t.table_name
      ),
      'privileges', (
        SELECT COALESCE(jsonb_agg(jsonb_build_object(
          'grantee', g.grantee,
          'privilege', g.privilege_type
        ) ORDER BY g.grantee, g.privilege_type), '[]'::jsonb)
        FROM information_schema.role_table_grants g
        WHERE g.table_schema = 'public'
          AND g.table_name = t.table_name
          AND g.grantee IN ('anon', 'authenticated', 'PUBLIC')
      ),
      'policies', (
        SELECT COALESCE(jsonb_agg(jsonb_build_object(
          'name', p.policyname,
          'cmd', p.cmd,
          'roles', p.roles,
          'qual', p.qual,
          'with_check', p.with_check
        ) ORDER BY p.policyname), '[]'::jsonb)
        FROM pg_policies p
        WHERE p.schemaname = 'public' AND p.tablename = t.table_name
      )
    )), '{}'::jsonb)
    FROM information_schema.tables t
    JOIN pg_tables pt ON pt.schemaname = t.table_schema AND pt.tablename = t.table_name
    WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
  ),
  'sinhvien_column_privileges', (
    SELECT COALESCE(jsonb_agg(jsonb_build_object(
      'grantee', grantee,
      'column', column_name,
      'privilege', privilege_type
    ) ORDER BY grantee, column_name, privilege_type), '[]'::jsonb)
    FROM information_schema.column_privileges
    WHERE table_schema = 'public'
      AND table_name = 'sinhvien'
      AND grantee IN ('anon', 'authenticated', 'PUBLIC')
  ),
  'views', (
    SELECT COALESCE(jsonb_agg(jsonb_build_object(
      'name', v.table_name,
      'options', c.reloptions,
      'definition', v.view_definition
    ) ORDER BY v.table_name), '[]'::jsonb)
    FROM information_schema.views v
    JOIN pg_class c ON c.relname = v.table_name
    JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = v.table_schema
    WHERE v.table_schema = 'public'
  ),
  'functions', (
    SELECT COALESCE(jsonb_agg(jsonb_build_object(
      'name', p.proname,
      'args', pg_get_function_identity_arguments(p.oid),
      'security_definer', p.prosecdef
    ) ORDER BY p.proname, pg_get_function_identity_arguments(p.oid)), '[]'::jsonb)
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
      AND p.prokind = 'f'
      AND NOT EXISTS (
        SELECT 1 FROM pg_depend d WHERE d.objid = p.oid AND d.deptype = 'e'
      )
  ),
  'triggers', (
    SELECT COALESCE(jsonb_agg(jsonb_build_object(
      'name', trigger_name,
      'table', event_object_table,
      'event', event_manipulation
    ) ORDER BY event_object_table, trigger_name, event_manipulation), '[]'::jsonb)
    FROM information_schema.triggers
    WHERE trigger_schema = 'public'
  )
)) AS supabase_schema_snapshot;
