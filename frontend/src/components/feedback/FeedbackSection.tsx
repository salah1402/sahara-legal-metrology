import React, { useState } from 'react';
import { Star, CheckCircle2, MessageSquareHeart } from 'lucide-react';

export interface FeedbackData {
  rating: number;
  comment: string;
  createdAt: string;
}

export interface FeedbackSectionProps {
  onFeedbackSubmit?: (data: FeedbackData) => Promise<void> | void;
  className?: string;
}

export const FeedbackSection: React.FC<FeedbackSectionProps> = ({
  onFeedbackSubmit,
  className = '',
}) => {
  const [rating, setRating] = useState<number>(0);
  const [hoverRating, setHoverRating] = useState<number>(0);
  const [comment, setComment] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isSubmitted, setIsSubmitted] = useState<boolean>(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (rating === 0 && !comment.trim()) return;

    setIsSubmitting(true);

    const feedbackPayload: FeedbackData = {
      rating,
      comment: comment.trim(),
      createdAt: new Date().toISOString(),
    };

    // Ready for future backend API integration
    try {
      if (onFeedbackSubmit) {
        await onFeedbackSubmit(feedbackPayload);
      }
    } catch (err) {
      console.warn('Feedback dispatch error:', err);
    } finally {
      setIsSubmitting(false);
      setIsSubmitted(true);
    }
  };

  const handleReset = () => {
    setRating(0);
    setHoverRating(0);
    setComment('');
    setIsSubmitted(false);
  };

  return (
    <section
      aria-label="User Feedback"
      className={`bg-white border border-slate-200/80 rounded-2xl shadow-subtle p-4 sm:p-5 transition-all ${className}`}
    >
      {isSubmitted ? (
        <div className="flex flex-col items-center text-center py-4 px-2 space-y-2 animate-fade-in">
          <div className="w-9 h-9 rounded-full bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 mb-0.5">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <h3 className="text-sm sm:text-base font-semibold text-slate-900">
            Thank you for your feedback.
          </h3>
          <p className="text-xs text-slate-500 max-w-md">
            Your response helps us improve SAHARA.
          </p>
          <button
            type="button"
            onClick={handleReset}
            className="mt-2 text-xs font-medium text-primary-800 hover:text-primary-900 hover:underline pt-1"
          >
            Submit another response
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-3.5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
            <div>
              <div className="flex items-center gap-1.5">
                <MessageSquareHeart className="w-4 h-4 text-primary-800 flex-shrink-0" />
                <h3 className="text-sm font-semibold text-slate-900">
                  Help us improve SAHARA
                </h3>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Your feedback helps us improve the legal metrology inspection experience.
              </p>
            </div>

            {/* 5-Star Rating */}
            <div className="flex items-center gap-1" role="group" aria-label="Rating">
              {[1, 2, 3, 4, 5].map((star) => {
                const isFilled = (hoverRating || rating) >= star;
                return (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setRating(star)}
                    onMouseEnter={() => setHoverRating(star)}
                    onMouseLeave={() => setHoverRating(0)}
                    aria-label={`Rate ${star} out of 5 stars`}
                    className="p-1 rounded hover:bg-slate-100 transition-colors focus:outline-none focus:ring-1 focus:ring-primary-800"
                  >
                    <Star
                      className={`w-4 h-4 sm:w-4.5 sm:h-4.5 transition-colors ${
                        isFilled
                          ? 'fill-amber-400 text-amber-400'
                          : 'text-slate-300 hover:text-slate-400'
                      }`}
                    />
                  </button>
                );
              })}
            </div>
          </div>

          {/* Comment textarea */}
          <div>
            <label htmlFor="feedback-comment" className="sr-only">
              Tell us about your experience
            </label>
            <textarea
              id="feedback-comment"
              rows={2}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Tell us about your experience..."
              className="w-full text-xs sm:text-sm bg-slate-50 border border-slate-200 rounded-xl p-2.5 sm:p-3 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-800 text-slate-800 placeholder-slate-400 transition-all resize-none"
            />
          </div>

          {/* Submit button */}
          <div className="flex justify-end items-center">
            <button
              type="submit"
              disabled={isSubmitting || (rating === 0 && !comment.trim())}
              className="inline-flex items-center justify-center text-xs font-medium px-4 py-2 bg-primary-800 hover:bg-primary-900 text-white rounded-lg transition-colors shadow-subtle disabled:opacity-50 disabled:cursor-not-allowed select-none"
            >
              {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
            </button>
          </div>
        </form>
      )}
    </section>
  );
};
