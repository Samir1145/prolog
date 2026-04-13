const pl = window.pl;
import ibcRules from './ibc_section7.pl';

/**
 * Checks the IBC Section 7 Adjudicating Authority Action based on the new rules.
 * 
 * @param {string} facts - The user's input facts as a string
 * @returns {Promise<Object>} A promise resolving to { isValid, aaAction, message }
 */
export const checkIbcSection7 = (facts) => {
  return new Promise((resolve, reject) => {
    const session = pl.create();
    
    // Combine base rules with the user's input facts dynamically
    const program = `${ibcRules}\n${facts}`;

    session.consult(program, {
      success: () => {
        // Query Adjudicating Authority Action (admit or reject)
        session.query("adjudicating_authority_action(Action, user_app).", {
          success: () => {
            session.answer({
              success: function(answer) {
                const action = answer.lookup("Action").id;
                
                if (action === 'admit') {
                  resolve({
                    isValid: true,
                    aaAction: 'admit',
                    message: "Valid filing. The Adjudicating Authority will ADMIT the application and commence CIRP."
                  });
                } else {
                  resolve({
                    isValid: true,
                    aaAction: 'reject',
                    message: "The application will be REJECTED. It may be incomplete, lack default verification, or proceedings are pending."
                  });
                }
              },
              fail: function() {
                resolve({ 
                  isValid: false, 
                  aaAction: null, 
                  message: "The Adjudicating Authority rules could not resolve any definitive action based on the inputs." 
                });
              },
              error: function(err) {
                reject(pl.format_answer(err));
              },
              limit: function() {
                reject("Resolution limit exceeded");
              }
            });
          },
          error: (err) => {
             reject(`AA Action Query error: ${err.toString()}`);
          }
        });
      },
      error: (err) => {
        reject(`Consult error: ${err.toString()}`);
      }
    });
  });
};

/**
 * Secondary helper to calculate minimum allottees needed using the Prolog logic block
 */
export const checkMinimumCreditors = (totalInClass) => {
  return new Promise((resolve, reject) => {
    const session = pl.create();
    session.consult(ibcRules, {
      success: () => {
         session.query(`minimum_creditors_required(section_21_6a_a, ${totalInClass}, Required).`, {
           success: () => {
             session.answer({
               success: function(answer) {
                 const required = answer.lookup("Required").value;
                 resolve(required);
               },
               fail: function() { resolve(null); },
               error: function() { resolve(null); },
               limit: function() { resolve(null); }
             });
           },
           error: () => resolve(null)
         })
      },
      error: () => resolve(null)
    });
  });
};

