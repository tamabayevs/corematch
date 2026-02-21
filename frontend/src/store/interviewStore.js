import { create } from "zustand";

export const useInterviewStore = create((set, get) => ({
  candidate: null,
  campaign: null,
  questions: [],
  answers: {},       // { [questionIndex]: { blob, uploaded, videoAnswerId } }
  currentStep: null, // 'welcome' | 'consent' | 'camera' | 'recording' | 'review' | 'confirmation'
  inviteExpiresAt: null,
  error: null,       // { type: 'expired' | 'submitted', data: {...} }

  setInviteData(data) {
    set({
      candidate: data.candidate,
      campaign: data.campaign,
      questions: data.questions,
      inviteExpiresAt: data.invite_expires_at,
      error: null,
    });
  },

  setError(type, data) {
    set({ error: { type, data } });
  },

  setAnswer(questionIndex, answerData) {
    set((state) => ({
      answers: { ...state.answers, [questionIndex]: answerData },
    }));
  },

  clearAnswer(questionIndex) {
    set((state) => {
      const newAnswers = { ...state.answers };
      delete newAnswers[questionIndex];
      return { answers: newAnswers };
    });
  },

  setCurrentStep(step) {
    set({ currentStep: step });
  },

  reset() {
    set({
      candidate: null,
      campaign: null,
      questions: [],
      answers: {},
      currentStep: null,
      inviteExpiresAt: null,
      error: null,
    });
  },
}));
