export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  public: {
    Tables: {
      activity: {
        Row: {
          action: string
          actor_id: string | null
          created_at: string
          id: string
          metadata: Json
          occurred_at: string
          organisation_id: string
          subject_id: string
          subject_type: string
          updated_at: string
        }
        Insert: {
          action: string
          actor_id?: string | null
          created_at?: string
          id?: string
          metadata?: Json
          occurred_at?: string
          organisation_id: string
          subject_id: string
          subject_type: string
          updated_at?: string
        }
        Update: {
          action?: string
          actor_id?: string | null
          created_at?: string
          id?: string
          metadata?: Json
          occurred_at?: string
          organisation_id?: string
          subject_id?: string
          subject_type?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "activity_organisation_id_fkey"
            columns: ["organisation_id"]
            isOneToOne: false
            referencedRelation: "organisation"
            referencedColumns: ["id"]
          },
        ]
      }
      app_user: {
        Row: {
          created_at: string
          email: string
          id: string
          locale: string | null
          organisation_id: string
          updated_at: string
        }
        Insert: {
          created_at?: string
          email: string
          id: string
          locale?: string | null
          organisation_id: string
          updated_at?: string
        }
        Update: {
          created_at?: string
          email?: string
          id?: string
          locale?: string | null
          organisation_id?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "app_user_organisation_id_fkey"
            columns: ["organisation_id"]
            isOneToOne: false
            referencedRelation: "organisation"
            referencedColumns: ["id"]
          },
        ]
      }
      application: {
        Row: {
          candidate_id: string
          created_at: string
          decided_at: string | null
          decided_by: string | null
          decision: Database["public"]["Enums"]["application_decision"]
          id: string
          job_id: string
          organisation_id: string
          updated_at: string
        }
        Insert: {
          candidate_id: string
          created_at?: string
          decided_at?: string | null
          decided_by?: string | null
          decision?: Database["public"]["Enums"]["application_decision"]
          id?: string
          job_id: string
          organisation_id: string
          updated_at?: string
        }
        Update: {
          candidate_id?: string
          created_at?: string
          decided_at?: string | null
          decided_by?: string | null
          decision?: Database["public"]["Enums"]["application_decision"]
          id?: string
          job_id?: string
          organisation_id?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "application_organisation_id_candidate_id_fkey"
            columns: ["organisation_id", "candidate_id"]
            isOneToOne: false
            referencedRelation: "candidate"
            referencedColumns: ["organisation_id", "id"]
          },
          {
            foreignKeyName: "application_organisation_id_decided_by_fkey"
            columns: ["organisation_id", "decided_by"]
            isOneToOne: false
            referencedRelation: "app_user"
            referencedColumns: ["organisation_id", "id"]
          },
          {
            foreignKeyName: "application_organisation_id_fkey"
            columns: ["organisation_id"]
            isOneToOne: false
            referencedRelation: "organisation"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "application_organisation_id_job_id_fkey"
            columns: ["organisation_id", "job_id"]
            isOneToOne: false
            referencedRelation: "job"
            referencedColumns: ["organisation_id", "id"]
          },
          {
            foreignKeyName: "application_organisation_id_job_id_fkey"
            columns: ["organisation_id", "job_id"]
            isOneToOne: false
            referencedRelation: "job_overview"
            referencedColumns: ["organisation_id", "id"]
          },
        ]
      }
      candidate: {
        Row: {
          created_at: string
          email: string | null
          full_name: string | null
          id: string
          location: string | null
          name_normalised: string | null
          organisation_id: string
          phone: string | null
          purged_at: string | null
          updated_at: string
        }
        Insert: {
          created_at?: string
          email?: string | null
          full_name?: string | null
          id?: string
          location?: string | null
          name_normalised?: string | null
          organisation_id: string
          phone?: string | null
          purged_at?: string | null
          updated_at?: string
        }
        Update: {
          created_at?: string
          email?: string | null
          full_name?: string | null
          id?: string
          location?: string | null
          name_normalised?: string | null
          organisation_id?: string
          phone?: string | null
          purged_at?: string | null
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "candidate_organisation_id_fkey"
            columns: ["organisation_id"]
            isOneToOne: false
            referencedRelation: "organisation"
            referencedColumns: ["id"]
          },
        ]
      }
      cv_file: {
        Row: {
          byte_size: number
          candidate_id: string | null
          content_hash: string
          created_at: string
          failure_reason: string | null
          id: string
          job_id: string | null
          mime_type: string
          organisation_id: string
          original_filename: string
          purged_at: string | null
          status: Database["public"]["Enums"]["cv_file_status"]
          storage_path: string
          updated_at: string
        }
        Insert: {
          byte_size: number
          candidate_id?: string | null
          content_hash: string
          created_at?: string
          failure_reason?: string | null
          id?: string
          job_id?: string | null
          mime_type: string
          organisation_id: string
          original_filename: string
          purged_at?: string | null
          status?: Database["public"]["Enums"]["cv_file_status"]
          storage_path: string
          updated_at?: string
        }
        Update: {
          byte_size?: number
          candidate_id?: string | null
          content_hash?: string
          created_at?: string
          failure_reason?: string | null
          id?: string
          job_id?: string | null
          mime_type?: string
          organisation_id?: string
          original_filename?: string
          purged_at?: string | null
          status?: Database["public"]["Enums"]["cv_file_status"]
          storage_path?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "cv_file_job_in_same_organisation"
            columns: ["organisation_id", "job_id"]
            isOneToOne: false
            referencedRelation: "job"
            referencedColumns: ["organisation_id", "id"]
          },
          {
            foreignKeyName: "cv_file_job_in_same_organisation"
            columns: ["organisation_id", "job_id"]
            isOneToOne: false
            referencedRelation: "job_overview"
            referencedColumns: ["organisation_id", "id"]
          },
          {
            foreignKeyName: "cv_file_organisation_id_candidate_id_fkey"
            columns: ["organisation_id", "candidate_id"]
            isOneToOne: false
            referencedRelation: "candidate"
            referencedColumns: ["organisation_id", "id"]
          },
          {
            foreignKeyName: "cv_file_organisation_id_fkey"
            columns: ["organisation_id"]
            isOneToOne: false
            referencedRelation: "organisation"
            referencedColumns: ["id"]
          },
        ]
      }
      deletion_request: {
        Row: {
          candidate_id: string
          completed_at: string | null
          created_at: string
          id: string
          organisation_id: string
          requested_at: string
          requested_by: string
          updated_at: string
        }
        Insert: {
          candidate_id: string
          completed_at?: string | null
          created_at?: string
          id?: string
          organisation_id: string
          requested_at?: string
          requested_by: string
          updated_at?: string
        }
        Update: {
          candidate_id?: string
          completed_at?: string | null
          created_at?: string
          id?: string
          organisation_id?: string
          requested_at?: string
          requested_by?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "deletion_request_organisation_id_candidate_id_fkey"
            columns: ["organisation_id", "candidate_id"]
            isOneToOne: false
            referencedRelation: "candidate"
            referencedColumns: ["organisation_id", "id"]
          },
          {
            foreignKeyName: "deletion_request_organisation_id_fkey"
            columns: ["organisation_id"]
            isOneToOne: false
            referencedRelation: "organisation"
            referencedColumns: ["id"]
          },
        ]
      }
      job: {
        Row: {
          created_at: string
          description: string | null
          id: string
          language_requirement: string | null
          location: string | null
          minimum_experience_years: number | null
          organisation_id: string
          preferred_skills: string[]
          required_skills: string[]
          title: string
          updated_at: string
          weights: Json
        }
        Insert: {
          created_at?: string
          description?: string | null
          id?: string
          language_requirement?: string | null
          location?: string | null
          minimum_experience_years?: number | null
          organisation_id: string
          preferred_skills?: string[]
          required_skills?: string[]
          title: string
          updated_at?: string
          weights: Json
        }
        Update: {
          created_at?: string
          description?: string | null
          id?: string
          language_requirement?: string | null
          location?: string | null
          minimum_experience_years?: number | null
          organisation_id?: string
          preferred_skills?: string[]
          required_skills?: string[]
          title?: string
          updated_at?: string
          weights?: Json
        }
        Relationships: [
          {
            foreignKeyName: "job_organisation_id_fkey"
            columns: ["organisation_id"]
            isOneToOne: false
            referencedRelation: "organisation"
            referencedColumns: ["id"]
          },
        ]
      }
      organisation: {
        Row: {
          created_at: string
          id: string
          locale: string
          name: string
          retention_months: number
          updated_at: string
        }
        Insert: {
          created_at?: string
          id?: string
          locale: string
          name: string
          retention_months?: number
          updated_at?: string
        }
        Update: {
          created_at?: string
          id?: string
          locale?: string
          name?: string
          retention_months?: number
          updated_at?: string
        }
        Relationships: []
      }
      parsed_profile: {
        Row: {
          confidence: number
          created_at: string
          cv_file_id: string
          extracted_at: string
          extraction_source: Database["public"]["Enums"]["extraction_source"]
          field_overrides: Json
          id: string
          is_current: boolean
          organisation_id: string
          profile: Json
          updated_at: string
          version: number
        }
        Insert: {
          confidence: number
          created_at?: string
          cv_file_id: string
          extracted_at?: string
          extraction_source: Database["public"]["Enums"]["extraction_source"]
          field_overrides?: Json
          id?: string
          is_current?: boolean
          organisation_id: string
          profile: Json
          updated_at?: string
          version: number
        }
        Update: {
          confidence?: number
          created_at?: string
          cv_file_id?: string
          extracted_at?: string
          extraction_source?: Database["public"]["Enums"]["extraction_source"]
          field_overrides?: Json
          id?: string
          is_current?: boolean
          organisation_id?: string
          profile?: Json
          updated_at?: string
          version?: number
        }
        Relationships: [
          {
            foreignKeyName: "parsed_profile_organisation_id_cv_file_id_fkey"
            columns: ["organisation_id", "cv_file_id"]
            isOneToOne: false
            referencedRelation: "cv_file"
            referencedColumns: ["organisation_id", "id"]
          },
          {
            foreignKeyName: "parsed_profile_organisation_id_fkey"
            columns: ["organisation_id"]
            isOneToOne: false
            referencedRelation: "organisation"
            referencedColumns: ["id"]
          },
        ]
      }
      score: {
        Row: {
          application_id: string
          components: Json
          cost_egp: number
          created_at: string
          id: string
          input_hash: string
          justification: string
          model_id: string
          organisation_id: string
          prompt_version: string
          provider: Database["public"]["Enums"]["model_provider"]
          summary: string
          summary_model_id: string | null
          summary_prompt_version: string | null
          summary_provider: Database["public"]["Enums"]["model_provider"] | null
          total: number
          updated_at: string
          weights_hash: string
        }
        Insert: {
          application_id: string
          components: Json
          cost_egp: number
          created_at?: string
          id?: string
          input_hash: string
          justification: string
          model_id: string
          organisation_id: string
          prompt_version: string
          provider: Database["public"]["Enums"]["model_provider"]
          summary: string
          summary_model_id?: string | null
          summary_prompt_version?: string | null
          summary_provider?:
            | Database["public"]["Enums"]["model_provider"]
            | null
          total: number
          updated_at?: string
          weights_hash: string
        }
        Update: {
          application_id?: string
          components?: Json
          cost_egp?: number
          created_at?: string
          id?: string
          input_hash?: string
          justification?: string
          model_id?: string
          organisation_id?: string
          prompt_version?: string
          provider?: Database["public"]["Enums"]["model_provider"]
          summary?: string
          summary_model_id?: string | null
          summary_prompt_version?: string | null
          summary_provider?:
            | Database["public"]["Enums"]["model_provider"]
            | null
          total?: number
          updated_at?: string
          weights_hash?: string
        }
        Relationships: [
          {
            foreignKeyName: "score_organisation_id_application_id_fkey"
            columns: ["organisation_id", "application_id"]
            isOneToOne: false
            referencedRelation: "application"
            referencedColumns: ["organisation_id", "id"]
          },
          {
            foreignKeyName: "score_organisation_id_application_id_fkey"
            columns: ["organisation_id", "application_id"]
            isOneToOne: false
            referencedRelation: "job_candidates"
            referencedColumns: ["organisation_id", "application_id"]
          },
          {
            foreignKeyName: "score_organisation_id_fkey"
            columns: ["organisation_id"]
            isOneToOne: false
            referencedRelation: "organisation"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      job_candidates: {
        Row: {
          application_id: string | null
          candidate_id: string | null
          confidence: number | null
          decided_at: string | null
          decided_by_email: string | null
          decision: Database["public"]["Enums"]["application_decision"] | null
          full_name: string | null
          job_id: string | null
          justification: string | null
          name_normalised: string | null
          organisation_id: string | null
          scored_at: string | null
          search_text: string | null
          total: number | null
        }
        Relationships: [
          {
            foreignKeyName: "application_organisation_id_candidate_id_fkey"
            columns: ["organisation_id", "candidate_id"]
            isOneToOne: false
            referencedRelation: "candidate"
            referencedColumns: ["organisation_id", "id"]
          },
          {
            foreignKeyName: "application_organisation_id_fkey"
            columns: ["organisation_id"]
            isOneToOne: false
            referencedRelation: "organisation"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "application_organisation_id_job_id_fkey"
            columns: ["organisation_id", "job_id"]
            isOneToOne: false
            referencedRelation: "job"
            referencedColumns: ["organisation_id", "id"]
          },
          {
            foreignKeyName: "application_organisation_id_job_id_fkey"
            columns: ["organisation_id", "job_id"]
            isOneToOne: false
            referencedRelation: "job_overview"
            referencedColumns: ["organisation_id", "id"]
          },
        ]
      }
      job_overview: {
        Row: {
          attention_count: number | null
          cv_count: number | null
          id: string | null
          location: string | null
          minimum_experience_years: number | null
          organisation_id: string | null
          processing_count: number | null
          ranked_count: number | null
          title: string | null
          updated_at: string | null
        }
        Relationships: [
          {
            foreignKeyName: "job_organisation_id_fkey"
            columns: ["organisation_id"]
            isOneToOne: false
            referencedRelation: "organisation"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Functions: {
      enqueue_cv_processing: {
        Args: { cv_file_id: string; locale: string }
        Returns: number
      }
      record_decision: {
        Args: {
          chosen: Database["public"]["Enums"]["application_decision"]
          reason?: string
          target_application: string
        }
        Returns: {
          decided_at: string
          decided_by_email: string
          decision: Database["public"]["Enums"]["application_decision"]
        }[]
      }
      request_candidate_deletion: {
        Args: { target_candidate: string }
        Returns: string
      }
      service_health: {
        Args: never
        Returns: {
          heartbeat_age_seconds: number
          oldest_message_seconds: number
          queue_depth: number
        }[]
      }
    }
    Enums: {
      application_decision: "undecided" | "shortlisted" | "rejected"
      cv_file_status:
        | "queued"
        | "extracting"
        | "extracted"
        | "needs_review"
        | "failed"
      extraction_source:
        | "native_text"
        | "vision_ocr"
        | "tesseract_ocr"
        | "manual"
      model_provider: "anthropic" | "openai"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends (DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never) = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends (PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never) = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      application_decision: ["undecided", "shortlisted", "rejected"],
      cv_file_status: [
        "queued",
        "extracting",
        "extracted",
        "needs_review",
        "failed",
      ],
      extraction_source: [
        "native_text",
        "vision_ocr",
        "tesseract_ocr",
        "manual",
      ],
      model_provider: ["anthropic", "openai"],
    },
  },
} as const

