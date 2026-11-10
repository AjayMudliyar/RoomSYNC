import { useCallback, useEffect, useMemo, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import * as SecureStore from "expo-secure-store";
import { RoomSyncApiClient, RoomSyncApiError } from "@roomsync/api-client";
import { MATCHING_BASELINE, type SystemStatusData } from "@roomsync/contracts";
import { nativeTheme } from "@roomsync/design-tokens/native";

function resolveAndroidApiOrigin(): string {
  const configured = process.env.EXPO_PUBLIC_API_BASE_URL;
  if (!configured) {
    return "http://10.0.2.2:8000";
  }
  return configured.replace(/\/api\/v1\/?$/, "");
}

export default function FoundationHomeScreen() {
  const [loading, setLoading] = useState(true);
  const [statusData, setStatusData] = useState<SystemStatusData | null>(null);
  const [requestId, setRequestId] = useState<string | null>(null);
  const [errorText, setErrorText] = useState<string | null>(null);
  const [secureStoreReady, setSecureStoreReady] = useState<boolean | null>(null);

  const client = useMemo(
    () =>
      new RoomSyncApiClient({
        baseOrigin: resolveAndroidApiOrigin(),
        platform: "android",
      }),
    [],
  );

  const checkConnectivity = useCallback(async () => {
    setLoading(true);
    setErrorText(null);
    try {
      const response = await client.getSystemStatus();
      setStatusData(response.data);
      setRequestId(response.meta.request_id);
    } catch (err) {
      if (err instanceof RoomSyncApiError) {
        setErrorText(`API error ${err.code} (${err.status})`);
      } else {
        setErrorText("Backend unreachable from Android client origin.");
      }
      setStatusData(null);
    } finally {
      setLoading(false);
    }
  }, [client]);

  useEffect(() => {
    void checkConnectivity();
    void SecureStore.isAvailableAsync()
      .then((available) => setSecureStoreReady(available))
      .catch(() => setSecureStoreReady(false));
  }, [checkConnectivity]);

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        <View style={styles.badgePill}>
          <Text style={styles.badgeText}>MILESTONE 0 ANDROID SHELL</Text>
        </View>

        <Text style={styles.headline}>Find your people before finding your place.</Text>
        <Text style={styles.subtitle}>
          RoomSync Android foundation built with Expo Router, Hardware SecureStore readiness, and
          ADR-003 Warm Tech Harmony tokens.
        </Text>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Backend API Connectivity</Text>
          {loading ? (
            <Text style={styles.mutedBody}>Checking Django /api/v1/system/status/...</Text>
          ) : errorText ? (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{errorText}</Text>
            </View>
          ) : statusData ? (
            <View style={styles.metaStack}>
              <Text style={styles.body}>
                Service: <Text style={styles.bold}>{statusData.service}</Text> ({statusData.status})
              </Text>
              {requestId ? <Text style={styles.mutedBody}>Request ID: {requestId}</Text> : null}
            </View>
          ) : null}

          <Text style={[styles.mutedBody, { marginTop: nativeTheme.spacing.sm }]}>
            SecureStore hardware keystore:{" "}
            {secureStoreReady === null
              ? "Checking..."
              : secureStoreReady
                ? "Available"
                : "Unavailable"}
          </Text>

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Re-check API connectivity"
            onPress={() => void checkConnectivity()}
            style={({ pressed }) => [styles.primaryButton, pressed && styles.primaryButtonPressed]}
          >
            <Text style={styles.primaryButtonLabel}>Check API Health</Text>
          </Pressable>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Matching Engine Baseline</Text>
          <Text style={styles.mutedBody}>
            {MATCHING_BASELINE.algorithmVersion} • {MATCHING_BASELINE.weightsVersion} (Schema v
            {MATCHING_BASELINE.questionSchemaVersion})
          </Text>
          <View style={styles.weightsGrid}>
            {Object.entries(MATCHING_BASELINE.weights).map(([key, weight]) => (
              <View key={key} style={styles.weightChip}>
                <Text style={styles.weightName}>{key.replaceAll("_", " ")}</Text>
                <Text style={styles.weightValue}>{weight}%</Text>
              </View>
            ))}
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: nativeTheme.colors.surface.canvas,
  },
  container: {
    padding: nativeTheme.spacing.section,
    gap: nativeTheme.spacing.cardCompact,
  },
  badgePill: {
    alignSelf: "flex-start",
    backgroundColor: nativeTheme.colors.action.tealTint,
    paddingHorizontal: nativeTheme.spacing.md,
    paddingVertical: nativeTheme.spacing.xs,
    borderRadius: nativeTheme.radii.full,
  },
  badgeText: {
    color: nativeTheme.colors.action.teal,
    fontSize: nativeTheme.typography.scale.labelSm.fontSize,
    fontWeight: "700",
    letterSpacing: 0.4,
  },
  headline: {
    color: nativeTheme.colors.brand.navy,
    fontSize: nativeTheme.typography.scale.headlineLg.fontSize,
    lineHeight: nativeTheme.typography.scale.headlineLg.lineHeight,
    fontWeight: "700",
  },
  subtitle: {
    color: nativeTheme.colors.text.secondary,
    fontSize: nativeTheme.typography.scale.bodyMd.fontSize,
    lineHeight: nativeTheme.typography.scale.bodyMd.lineHeight,
  },
  card: {
    backgroundColor: nativeTheme.colors.surface.card,
    borderRadius: nativeTheme.radii.lg,
    borderWidth: 1,
    borderColor: nativeTheme.colors.border.subtle,
    padding: nativeTheme.spacing.cardCompact,
    gap: nativeTheme.spacing.sm,
    ...nativeTheme.elevation.card,
  },
  cardTitle: {
    color: nativeTheme.colors.brand.navy,
    fontSize: nativeTheme.typography.scale.titleMd.fontSize,
    fontWeight: "600",
  },
  metaStack: {
    gap: nativeTheme.spacing.xs,
  },
  body: {
    color: nativeTheme.colors.text.primary,
    fontSize: nativeTheme.typography.scale.bodyMd.fontSize,
  },
  bold: {
    fontWeight: "700",
  },
  mutedBody: {
    color: nativeTheme.colors.text.muted,
    fontSize: nativeTheme.typography.scale.bodySm.fontSize,
  },
  errorBox: {
    backgroundColor: nativeTheme.colors.status.dangerBg,
    borderWidth: 1,
    borderColor: nativeTheme.colors.status.dangerBorder,
    borderRadius: nativeTheme.radii.md,
    padding: nativeTheme.spacing.md,
  },
  errorText: {
    color: nativeTheme.colors.status.danger,
    fontSize: nativeTheme.typography.scale.bodySm.fontSize,
  },
  primaryButton: {
    marginTop: nativeTheme.spacing.sm,
    minHeight: nativeTheme.touchTarget.minPx,
    borderRadius: nativeTheme.radii.md,
    backgroundColor: nativeTheme.colors.action.teal,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: nativeTheme.spacing.cardCompact,
  },
  primaryButtonPressed: {
    backgroundColor: nativeTheme.colors.action.tealHover,
  },
  primaryButtonLabel: {
    color: nativeTheme.colors.text.onDark,
    fontSize: nativeTheme.typography.scale.labelLg.fontSize,
    fontWeight: "600",
  },
  weightsGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: nativeTheme.spacing.sm,
    marginTop: nativeTheme.spacing.xs,
  },
  weightChip: {
    width: "48%",
    backgroundColor: nativeTheme.colors.surface.low,
    borderRadius: nativeTheme.radii.md,
    paddingHorizontal: nativeTheme.spacing.md,
    paddingVertical: nativeTheme.spacing.sm,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  weightName: {
    color: nativeTheme.colors.text.secondary,
    fontSize: nativeTheme.typography.scale.bodySm.fontSize,
    textTransform: "capitalize",
    flexShrink: 1,
  },
  weightValue: {
    color: nativeTheme.colors.brand.navy,
    fontSize: nativeTheme.typography.scale.labelMd.fontSize,
    fontWeight: "700",
  },
});
