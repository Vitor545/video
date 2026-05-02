{{- define "video-app.name" -}}
video-app
{{- end -}}

{{- define "video-app.namespace" -}}
{{ .Values.namespace | default .Release.Namespace }}
{{- end -}}

{{- define "video-app.labels" -}}
app.kubernetes.io/name: {{ include "video-app.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{- end -}}

{{- define "video-app.databaseUrl" -}}
postgresql+asyncpg://{{ .Values.config.database.user }}:{{ .Values.config.database.password }}@video-postgres:5432/{{ .Values.config.database.name }}
{{- end -}}

{{- define "video-app.syncDatabaseUrl" -}}
postgresql+psycopg2://{{ .Values.config.database.user }}:{{ .Values.config.database.password }}@video-postgres:5432/{{ .Values.config.database.name }}
{{- end -}}

{{- define "video-app.backendImage" -}}
{{ .Values.image.registry }}/{{ .Values.image.backend.repository }}:{{ .Values.image.tag }}
{{- end -}}

{{- define "video-app.frontendImage" -}}
{{ .Values.image.registry }}/{{ .Values.image.frontend.repository }}:{{ .Values.image.tag }}
{{- end -}}
