const pl = window.pl;
import mediationRules from './mediation.pl';

/**
 * Checks if a case is eligible for mediation based on the Indian Mediation Act 2023 rules.
 * 
 * @param {string} facts - The user's input facts as a string (e.g., "is_commercial(true). value(60000).")
 * @returns {Promise<boolean|string>} A promise that resolves to true (eligible), false (ineligible), or an error message.
 */
export const checkMediation = (facts, value) => {
  return new Promise((resolve, reject) => {
    // 1. Creates a new pl.create() session
    const session = pl.create();

    // 2. Combine the base rules with the user's input facts
    const program = `${mediationRules}\n${facts}`;

    // 3. Consults the mediation.pl file (with integrated user facts)
    session.consult(program, {
      success: () => {
        // 4. Queries if it's eligible using the provided value
        session.query(`is_eligible(${value}).`, {
          success: () => {
            session.answer({
              success: function(answer) {
                // The query found a match! It is eligible.
                resolve(true);
              },
              fail: function() {
                // The knowledge base could not satisfy the query. It is ineligible.
                resolve(false);
              },
              error: function(err) {
                // Caught a Prolog error (e.g. syntax)
                reject(pl.format_answer(err));
              },
              limit: function() {
                reject("Resolution limit exceeded");
              }
            });
          },
          error: (err) => {
            reject(`Query error: ${err.toString()}`);
          }
        });
      },
      error: (err) => {
        reject(`Consult error: ${err.toString()}`);
      }
    });
  });
};
