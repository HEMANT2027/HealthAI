import React, { useEffect, useState, useMemo } from "react";
import { useLocation } from "react-router-dom";

function Section({ title, children, right }) {
  return (
    <section className="bg-white/90 backdrop-blur-sm border border-gray-200 rounded-2xl shadow-sm p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-bold text-gray-900">{title}</h3>
        {right}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function Pill({ children }) {
  return (
    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-vibrant-blue border border-blue-100">
      {children}
    </span>
  );
}

export default function Profile() {
  const location = useLocation();
  const pathParts = location.pathname.split("/");
  const pseudonym_id = pathParts[pathParts.length - 1] || location.state?.pseudonym_id;
  const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [recommendation, setRecommendation] = useState(null);

  useEffect(() => {
    if (!pseudonym_id) return;
    const token = localStorage.getItem("token");

    const fetchStored = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE_URL}/tourism/stored/${pseudonym_id}`, {
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        });

        if (res.ok) {
          const data = await res.json();
          setRecommendation(data.recommendation || null);
          setLoading(false);
          return;
        }

        // If not found, call generate endpoint then re-fetch stored
        if (res.status === 404) {
          const genRes = await fetch(`${API_BASE_URL}/tourism/recommend/${pseudonym_id}`, {
            method: "GET",
            headers: {
              "Content-Type": "application/json",
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
          });

          if (!genRes.ok) {
            const err = await genRes.json().catch(() => ({}));
            throw new Error(err.detail || `Generate failed: ${genRes.status}`);
          }

          const storedRes = await fetch(`${API_BASE_URL}/tourism/stored/${pseudonym_id}`, {
            headers: {
              "Content-Type": "application/json",
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
          });

          if (!storedRes.ok) {
            const genData = await genRes.json().catch(() => ({}));
            setRecommendation({
              pseudonym_id,
              json: genData.json || null,
              raw: genData.raw || null,
              created_at: new Date().toISOString(),
              patient_snapshot: genData.patient || null,
              medical_snapshot: genData.medical || null,
            });
            setLoading(false);
            return;
          }

          const storedData = await storedRes.json();
          setRecommendation(storedData.recommendation || null);
          setLoading(false);
          return;
        }

        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Status ${res.status}`);
      } catch (err) {
        setError(err.message || "Failed to fetch recommendation");
        setLoading(false);
      }
    };

    fetchStored();
  }, [pseudonym_id]);

  // parse recommendation into structured UI data
  const data = useMemo(() => {
    if (!recommendation) return null;

    let payload = recommendation.json || null;
    if (!payload && recommendation.raw) {
      try {
        payload = JSON.parse(recommendation.raw);
      } catch (e) {
        payload = null;
      }
    }

    const itineraryDays =
      payload?.Itinerary ||
      payload?.itinerary ||
      (payload?.ItineraryDays && Array.isArray(payload.ItineraryDays) ? payload.ItineraryDays : []) ||
      (payload?.itinerary?.days && Array.isArray(payload.itinerary.days) ? payload.itinerary.days : []);

    const hospital_suggestions =
      payload?.HospitalRecommendations ||
      payload?.hospital_suggestions ||
      payload?.hospital_recommendations ||
      [];

    const sightseeing =
      payload?.RecoveryAndSightseeing ||
      payload?.Recovery_and_Sightseeing ||
      payload?.recovery_and_sightseeing ||
      payload?.sightseeing ||
      [];

    return {
      itineraryDays: Array.isArray(itineraryDays) ? itineraryDays : [],
      hospital_suggestions: Array.isArray(hospital_suggestions) ? hospital_suggestions : [],
      sightseeing: Array.isArray(sightseeing) ? sightseeing : [],
      created_at: recommendation.created_at || recommendation.updated_at || null,
      raw: recommendation.raw || null,
      json: payload || null,
      patient_snapshot: recommendation.patient_snapshot || null,
      medical_snapshot: recommendation.medical_snapshot || null,
    };
  }, [recommendation]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-200 via-white to-teal-100 py-10">
      <div className="max-w-6xl mx-auto px-4">
        <div className="mb-6">
          <h1 className="text-3xl font-extrabold text-gray-900">Patient Profile</h1>
          <p className="mt-1 text-gray-600">Pseudonym ID: <span className="font-medium">{pseudonym_id}</span></p>
        </div>

        {loading && <div className="text-gray-600">Loading…</div>}
        {error && <div className="p-4 bg-red-50 border border-red-200 rounded text-sm">{error}</div>}

        {!loading && !error && (
          <div className="grid lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <Section title="Itinerary">
                {(!data || data.itineraryDays.length === 0) ? (
                  <div className="text-sm text-gray-500 p-4">No itinerary available.</div>
                ) : (
                  <ol className="space-y-4">
                    {data.itineraryDays.map((d, i) => {
                      const dayLabel = d.Day || d.day || d.DayNumber || i + 1;
                      const activity = d.Activity || d.activity || d.plan || d.activity || d.Activity || "";
                      const notes = d.Notes || d.notes || d.Notes || "";
                      const location = d.Location || d.location || d.place || d.Place || "";
                      return (
                        <li key={i} className="rounded-lg border border-gray-200 p-4 bg-white">
                          <div className="flex items-start justify-between gap-4">
                            <div>
                              <div className="text-sm text-gray-500">Day {dayLabel}</div>
                              <div className="mt-1 text-lg font-semibold text-gray-900">{activity || "Activity"}</div>
                              {notes && <div className="mt-2 text-sm text-gray-600">{notes}</div>}
                            </div>
                            {location && (
                              <div className="text-right">
                                <Pill>{location}</Pill>
                              </div>
                            )}
                          </div>
                        </li>
                      );
                    })}
                  </ol>
                )}
              </Section>
            </div>

            <div className="space-y-6">
              <Section title="Hospital Suggestions" right={<Pill>{(data?.hospital_suggestions || []).length} options</Pill>}>
                {(!data || data.hospital_suggestions.length === 0) ? (
                  <div className="text-sm text-gray-500 p-4">No hospital suggestions available.</div>
                ) : (
                  <ul className="space-y-3">
                    {data.hospital_suggestions.map((h, i) => {
                      const name = h.Name || h.name || h.hospital || h.Hospital || "Hospital";
                      const city = h.City || h.city || h.location || h.CityName || "";
                      const acc = h.Accreditation || h.accreditation || h.Accred || "";
                      const cost = h.ApproxTreatmentCost || h.est_cost_usd || h.cost || "";
                      const website = h.Website || h.website || h.url || h.contact || "";
                      return (
                        <li key={i} className="rounded-lg border border-gray-200 p-4 bg-white">
                          <div className="flex flex-col gap-2">
                            <div className="flex items-center justify-between">
                              <div>
                                <div className="font-semibold text-gray-900">{name}</div>
                                <div className="text-sm text-gray-600">{city} {acc ? `• ${acc}` : ""}</div>
                              </div>
                              <div className="text-right">
                                {cost && <div className="text-sm text-gray-800 font-medium">${cost}</div>}
                                {website && (
                                  <a
                                    href={website}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="mt-2 inline-block text-xs text-blue-600 hover:underline"
                                  >
                                    Visit site ↗
                                  </a>
                                )}
                              </div>
                            </div>
                            {h.Specialization || h.specialty || h.Speciality ? (
                              <div className="text-sm text-gray-700">{h.Specialization || h.specialty || h.Speciality}</div>
                            ) : null}
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </Section>

              {/* Sightseeing moved to right column under hospitals as requested */}
              <Section title="Sightseeing & Recovery Spots">
                {(!data || data.sightseeing.length === 0) ? (
                  <div className="text-sm text-gray-500 p-4">No sightseeing / recovery suggestions available.</div>
                ) : (
                  <div className="grid sm:grid-cols-1 gap-4">
                    {data.sightseeing.map((s, i) => {
                      const place = s.Place || s.place || s.Name || s.PlaceName || s;
                      const reason = s.WhyRecommended || s.reason || s.Why || s.Reason || "";
                      return (
                        <div key={i} className="rounded-lg border border-gray-200 p-4 bg-white">
                          <div className="flex items-start justify-between">
                            <div>
                              <div className="font-semibold text-gray-900">{place}</div>
                              {reason && <div className="mt-1 text-sm text-gray-600">{reason}</div>}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </Section>

              <Section title="Stored Data">
                <div className="text-sm text-gray-600 mb-3">Stored snapshots and raw output (for debugging)</div>
                <details className="bg-gray-50 p-3 rounded">
                  <summary className="cursor-pointer text-sm font-medium">Show stored JSON / raw</summary>
                  <pre className="mt-2 text-xs whitespace-pre-wrap">{JSON.stringify(data?.json || { raw: data?.raw }, null, 2)}</pre>
                </details>
              </Section>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}