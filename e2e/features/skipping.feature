Feature: Skipping the next pub
  People using AutoPub are marked as going to every pub. They can skip the next one, even before it is chosen.

  Scenario: Skipping before the next pub is chosen
    Given I am signed in as a member using AutoPub
    When I open "/pub/"
    And I click the "Skip next pub" button
    Then I should see "You've skipped the next pub"
    And I should see a "Undo skip" button
    And I should not see a "Skip next pub" button

  Scenario: Undoing a skip
    Given I am signed in as a member using AutoPub
    And I have skipped the next pub
    When I open "/pub/"
    And I click the "Undo skip" button
    Then I should see "AutoPub will add you"
    And I should see a "Skip next pub" button

  Scenario: Skipping a pub that has been chosen
    Given I am signed in as a member using AutoPub
    And the next pub is at "The Anchor"
    And I am going to it through AutoPub
    When I open "/pub/"
    Then I should see "You're going"
    When I click the "Skip next pub" button
    Then I should see "You skipped this one"
    And I should see a "Undo skip" button

  Scenario: Members not using AutoPub cannot skip
    Given I am signed in as a member
    When I open "/pub/"
    Then I should not see a "Skip next pub" button

  Scenario: Turning on AutoPub makes skipping available
    Given I am signed in as a member
    When I open "/pub/"
    And I click the "Turn on AutoPub" button
    Then I should see a "Turn off AutoPub" button
    And I should see a "Skip next pub" button
